import json
import logging
import boto3
from typing import Dict, Any

import opensearchpy
import os

from opensearchpy import OpenSearch

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Initialize clients
sqs = boto3.client('sqs')

TASK_INDEX_LOG = os.getenv("TASK_INDEX_LOG", "INDEX_LOG")
INDEX_NAME = os.getenv("INDEX_NAME", "audit-logs")


def get_queue_url(queue_name: str) -> str:
    """Get the URL of the SQS queue."""
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        return response['QueueUrl']
    except Exception as e:
        logger.error(f"Error getting queue URL: {str(e)}")
        raise


def process_message(opensearch: OpenSearch, message: Dict[str, Any]) -> None:
    """Process a single SQS message."""
    try:
        body = json.loads(message['body'])
        task_type = body.get('task_type')

        if task_type == TASK_INDEX_LOG:
            process_index_log(opensearch, body)
        else:
            logger.warning(f"Unknown task type: {task_type}")

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.exception(e)
        raise


def process_index_log(opensearch: OpenSearch, body: Dict[str, Any]) -> None:
    """Process INDEX_LOG task."""
    try:
        create_index(opensearch)
        logger.debug(f"body: {body}")
        payload = body['payload']
        logger.info(f"Processing log index task: {payload['id']}")
        opensearch.index(
            index=INDEX_NAME,
            id=payload["id"],
            body={
                "id": payload["id"],
                "tenant_id": payload["tenant_id"],
                "message": payload["message"],
                "log_metadata": json.dumps(payload["log_metadata"]) if payload["log_metadata"] else "",
                "created_at": payload["created_at"],
                "user_id": payload["user_id"],
                "action": payload["action"],
                "resource_type": payload["resource_type"],
                "severity": payload["severity"]
            }
        )
        logger.info(f"Indexed log entry: {payload['id']}")

    except Exception as e:
        logger.error(f"Error indexing log: {str(e)}")
        raise


def create_index(opensearch: OpenSearch) -> None:
    """
    Create the audit logs index in OpenSearch with appropriate mappings.
    """
    if not opensearch.indices.exists(index=INDEX_NAME):
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
        opensearch.indices.create(index=INDEX_NAME, body=mappings)
        logger.info(f"Created OpenSearch index: {INDEX_NAME}")
    else:
        logger.info(f"OpenSearch index: {INDEX_NAME} already exists")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda function handler."""
    try:
        opensearch = opensearchpy.OpenSearch(
            hosts=[os.getenv("OPENSEARCH_URL", "http://opensearch_con:9200")],
            timeout=30
        )
        # Get messages from the event
        records = event.get('Records', [])

        if not records:
            logger.warning("No records found in event")
            return {
                'statusCode': 200,
                'body': 'No messages to process'
            }

        # Process each message
        for record in records:
            process_message(opensearch, record)

        return {
            'statusCode': 200,
            'body': f'Processed {len(records)} messages'
        }

    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': str(e)
        }
