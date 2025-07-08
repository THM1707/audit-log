"""Service layer for audit log search functionality."""
import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import opensearchpy

from src.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SearchService:
    """Service class for handling audit log search operations.

    This service provides methods for searching audit logs using OpenSearch.
    It handles both database and OpenSearch operations.
    """

    INDEX_NAME = "audit_logs"

    def __init__(self):
        """
        Initialize the SearchService.

        Creates a connection to OpenSearch using the configured URL.
        """
        self.opensearch = opensearchpy.OpenSearch(
            hosts=[settings.OPENSEARCH_URL],
            timeout=30
        )

    def create_index(self) -> None:
        """
        Create the audit logs index in OpenSearch with appropriate mappings.
        """
        if not self.opensearch.indices.exists(index=self.INDEX_NAME):
            mappings = {
                "mappings": {
                    "properties": {
                        "id": {"type": "keyword"},
                        "tenant_id": {"type": "keyword"},
                        "message": {"type": "text"},
                        "log_metadata": {"type": "text"},
                        "created_at": {"type": "date"},
                        "user_id": {"type": "keyword"},
                        "action": {"type": "keyword"},
                        "resource_type": {"type": "keyword"},
                        "severity": {"type": "keyword"}
                    }
                }
            }
            self.opensearch.indices.create(index=self.INDEX_NAME, body=mappings)
            logger.info(f"Created OpenSearch index: {self.INDEX_NAME}")
        else:
            logger.info(f"OpenSearch index: {self.INDEX_NAME} already exists")

    async def index_log(self, log: Dict[str, Any]) -> None:
        """
        Index a single audit log entry in OpenSearch.

        Args:
            log (Dict[str, Any]): Audit log entry to index
        """
        try:
            self.opensearch.index(
                index=self.INDEX_NAME,
                id=log["id"],
                body={
                    "id": log["id"],
                    "tenant_id": log["tenant_id"],
                    "message": log["message"],
                    "log_metadata": json.dumps(log["log_metadata"]) if log["log_metadata"] else "",
                    "created_at": log["created_at"],
                    "user_id": log["user_id"],
                    "action": log["action"],
                    "resource_type": log["resource_type"],
                    "severity": log["severity"]
                }
            )
            logger.info(f"Indexed log entry: {log['id']}")
        except Exception as e:
            logger.error(f"Failed to index log entry: {log['id']}, Error: {str(e)}")
            raise

    async def search_logs(
        self,
        tenant_id: int,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search audit logs using OpenSearch with full-text search.

        Args:
            tenant_id (int): ID of the tenant
            query (Optional[str]): Search query for message and metadata
            filters (Optional[Dict[str, Any]]): Additional filters
            page (int): Page number
            limit (int): Number of results per page

        Returns:
            List[Dict[str, Any]]: List of search results

        Raises:
            Exception: If search fails
        """
        body = {
            "query": {
                "bool": {
                    "must": [
                        {"term": {"tenant_id": str(tenant_id)}},
                    ]
                }
            },
            "size": limit,
            "from": (page - 1) * limit
        }

        # Add a full-text search query if provided
        if query:
            body["query"]["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["message", "log_metadata"],
                    "type": "best_fields",
                    "operator": "AND"
                }
            })

        # Add additional filters
        if filters:
            for field, value in filters.items():
                if isinstance(value, datetime):
                    body["query"]["bool"]["must"].append({
                        "range": {
                            field: {"gte": value.isoformat()}
                        }
                    })
                else:
                    body["query"]["bool"]["must"].append({
                        "term": {field: value}
                    })

        try:
            response = self.opensearch.search(
                index=self.INDEX_NAME,
                body=body
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
