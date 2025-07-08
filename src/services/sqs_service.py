"""Service layer for SQS-based background tasks."""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import boto3

from src.core import config
from src.enums.task_type import TaskType
from src.services.search_service import SearchService

settings = config.get_settings()
logger = logging.getLogger(__name__)


class SQSService:
    """Service class for handling SQS-based background tasks."""

    def __init__(self):
        self.client = boto3.client('sqs', **settings.sqs_config)
        response = self.client.get_queue_url(QueueName=settings.SQS_QUEUE_NAME)
        self.queue_url = response['QueueUrl']
        self.search_service = SearchService()

    async def send_task(self, task_type: TaskType, payload: Dict[str, Any]) -> str:
        """
        Send a background task to SQS asynchronously.

        Args:
            task_type (TaskType): Type of task
            payload (Dict[str, Any]): Task payload

        Returns:
            str: Message ID

        Raises:
            ValueError: If an invalid task type is provided
            Exception: If message sending fails
        """
        message = {
            'task_type': task_type,
            'payload': payload,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'retries': 0
        }

        if not isinstance(task_type, TaskType):
            raise ValueError(f"Invalid task type: {task_type}")

        try:
            response = self.client.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message),
                MessageAttributes={
                    'task_type': {
                        'DataType': 'String',
                        'StringValue': str(task_type)
                    }
                }
            )
            msg_id = response['MessageId']
            logger.info(f"Task {msg_id} sent to SQS: {task_type}")
            return msg_id
        except Exception as e:
            logger.error(f"Error sending SQS message: {str(e)}")
            raise
