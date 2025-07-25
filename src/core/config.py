from functools import lru_cache
from typing import Dict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "local"

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/audit_log"

    # Security
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Optional configuration
    DEBUG: bool = True
    LOG_LEVEL: str = "info"

    # AWS
    AWS_REGION: str = "ap-northeast-1"  # Default region for LocalStack
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"
    SQS_ENDPOINT_URL: str = "http://localhost:4566"
    SQS_QUEUE_NAME: str = "audit-log-queue"

    # OpenSearch
    OPENSEARCH_URL: str = "http://localhost:9200"

    # Data Retention
    LOG_RETENTION_DAYS: int = 90

    # Data Compression
    LOG_COMPRESSION_INTERVAL: int = 30

    # WebSocket
    WEBSOCKET_MAX_CONNECTIONS: int = 100

    # Export
    EXPORT_MAX_ROWS: int = 10000

    # CORS
    CORS_ORIGINS: str = "*"
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "*"
    CORS_HEADERS: str = "*"

    # CUSTOM HEADERS
    X_TENANT_ID: str = "X-Tenant-Id"
    X_USER_ID: str = "X-User-Id"
    X_USER_NAME: str = "X-User-Name"
    X_USER_ROLE: str = "X-User-Role"

    model_config = SettingsConfigDict(
        env_file=".env",  # Load variables from .env file
        env_file_encoding="utf-8",  # Encoding for the .env file
        case_sensitive=False,  # Environment variable names are case-insensitive by default
        extra="ignore",
    )

    # Helper methods
    def get_cors_config(self) -> Dict[str, str]:
        """Get CORS configuration from settings."""
        return {
            "allow_origins": self.CORS_ORIGINS.split(",") if isinstance(self.CORS_ORIGINS, str) else self.CORS_ORIGINS,
            "allow_credentials": self.CORS_CREDENTIALS,
            "allow_methods": self.CORS_METHODS.split(",") if isinstance(self.CORS_METHODS, str) else self.CORS_METHODS,
            "allow_headers": self.CORS_HEADERS.split(",") if isinstance(self.CORS_HEADERS, str) else self.CORS_HEADERS,
        }

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT == "local"

    @property
    def sqs_config(self) -> dict:
        config = {
            "region_name": self.AWS_REGION,
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
            "endpoint_url": self.SQS_ENDPOINT_URL,
        }

        return config


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    return settings
