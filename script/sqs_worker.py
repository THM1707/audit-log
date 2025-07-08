"""Background worker for processing SQS messages."""

import asyncio
import json
import logging
import signal

import boto3
from botocore.exceptions import ClientError

from src.core import config
from src.enums.task_type import TaskType
from src.services.search_service import SearchService

logger = logging.getLogger(__name__)
settings = config.get_settings()


class SQSWorker:
    """Worker class for processing SQS messages."""

    def __init__(self):
        """Initialize the worker."""
        self.client = None
        self.queue_url = None
        self.running = True
        self._initialize_client()
        self.search_service = SearchService()
        self.search_service.create_index()

    def _initialize_client(self):
        """Initialize SQS client."""
        try:
            self.client = boto3.client('sqs', **settings.sqs_config)
            self._ensure_queue_exists()
        except Exception as e:
            logger.error(f"Failed to initialize SQS client: {e}")
            raise

    def _ensure_queue_exists(self):
        """Ensure the SQS queue exists."""
        try:
            response = self.client.get_queue_url(QueueName=settings.QUEUE_NAME)
            self.queue_url = response['QueueUrl']
            logger.info(f"Using queue: {self.queue_url}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                logger.info(f"Creating queue: {settings.QUEUE_NAME}")
                response = self.client.create_queue(
                    QueueName=settings.QUEUE_NAME,
                    Attributes={
                        'MessageRetentionPeriod': '1209600',  # 14 days
                    }
                )
                self.queue_url = response['QueueUrl']
                logger.info(f"Created queue: {self.queue_url}")
            else:
                logger.error(f"Error accessing queue: {e}")
                raise

    async def process_message(self, message: dict) -> None:
        """Process a single SQS message."""
        body = {}
        try:
            body = json.loads(message['Body'])
            task_type = body.get('task_type')
            payload = body.get('payload')

            if not task_type or not payload:
                raise ValueError("Missing task_type or payload")

            logger.info(f"Processing {task_type} task")

            if task_type == TaskType.INDEX_LOG:
                await self._process_index_log(payload)
            else:
                logger.warning(f"Unknown task type: {task_type}")

            # Delete message if successful
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.info(f"Successfully processed message: {message['MessageId']}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Handle retries if needed
            if not body:
                return
            retries = body.get('retries', 0) + 1
            if retries < settings.SQS_MAX_RETRIES:
                self._send_to_dead_letter_queue(message, retries)
            else:
                logger.error(f"Max retries reached for message: {message['MessageId']}")

    async def _process_index_log(self, payload: dict) -> None:
        """Process INDEX_LOG task."""
        try:
            await self.search_service.index_log(payload)
            logger.info(f"Successfully indexed log: {payload['id']}")
        except Exception as e:
            logger.error(f"Error indexing log: {str(e)}")
            raise

    def _send_to_dead_letter_queue(self, message: dict, retries: int) -> None:
        """Send the message to dead letter queue."""
        try:
            body = json.loads(message['Body'])
            body['retries'] = retries

            # Send to DLQ if configured
            if settings.DLQ_QUEUE_URL:
                self.client.send_message(
                    QueueUrl=settings.DLQ_QUEUE_URL,
                    MessageBody=json.dumps(body),
                    MessageAttributes={
                        'task_type': {
                            'DataType': 'String',
                            'StringValue': body['task_type']
                        }
                    }
                )
                logger.info(f"Message sent to DLQ: {message['MessageId']}")
            else:
                logger.warning("No DLQ configured, message will be retried")

        except Exception as e:
            logger.error(f"Error sending to DLQ: {str(e)}")
            raise

    async def run(self):
        """Run the worker."""
        logger.info("Starting SQS worker...")

        while self.running:
            try:
                # Receive messages with long polling
                response = self.client.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=settings.SQS_MAX_MESSAGES,
                    WaitTimeSeconds=settings.SQS_WAIT_TIME_SECONDS,
                    VisibilityTimeout=settings.SQS_VISIBILITY_TIMEOUT
                )

                messages = response.get('Messages', [])
                if messages:
                    logger.info(f"Received {len(messages)} messages")

                    # Process messages concurrently
                    await asyncio.gather(*[
                        self.process_message(message)
                        for message in messages
                    ])

            except ClientError as e:
                logger.error(f"Error receiving messages: {str(e)}")
                await asyncio.sleep(5)  # Backoff on error
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                await asyncio.sleep(1)

    async def shutdown(self):
        """Shutdown the worker."""
        self.running = False
        loop = asyncio.get_running_loop()
        if loop.is_running():
            print("Stopping event loop.")
            loop.stop()
        logger.info("Shutting down SQS worker...")


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('sqs_worker.log')
        ]
    )


def main():
    """Main entry point."""
    setup_logging()
    worker = SQSWorker()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    # Run until encounter Interrupt or Terminate signal
    for signal_name in ('SIGINT', 'SIGTERM'):
        loop.add_signal_handler(
            getattr(signal, signal_name),
            lambda: asyncio.create_task(worker.shutdown()),
        )

    try:
        loop.run_until_complete(worker.run())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
