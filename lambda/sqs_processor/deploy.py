import logging
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

SQS_ENDPOINT_URL = os.getenv("SQS_ENDPOINT_URL", "http://localstack-main:4566")
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL", "http://localstack-main:4566/000000000000/audit-log-queue")
AWS_REGION = os.getenv("AWS_REGION", "ap-northeast-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
FUNCTION_NAME = os.getenv("LAMBDA_FUNCTION_NAME", "sqs_processor")
INDEX_NAME = os.getenv("INDEX_NAME", "audit-logs")

aws_config = {
    "endpoint_url": SQS_ENDPOINT_URL,
    "region_name": AWS_REGION,
    "aws_access_key_id": AWS_ACCESS_KEY_ID,
    "aws_secret_access_key": "test",
}


def create_zip():
    """Create a zip file containing the Lambda function code."""
    try:
        # Create build directory
        build_dir = Path("build")
        if build_dir.exists():
            shutil.rmtree(build_dir)
        build_dir.mkdir(parents=True)

        # Install dependencies directly to the build directory
        requirements_path = Path("requirements.txt")
        if requirements_path.exists():
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(requirements_path), "--target", str(build_dir)],
                check=True,
            )
        else:
            # Install required packages if no requirements.txt
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "boto3", "opensearch-py", "--target", str(build_dir)],
                check=True,
            )

        # Copy handler.py to the root of the build directory
        handler_path = Path("handler.py")
        if handler_path.exists():
            shutil.copy2(handler_path, build_dir / handler_path.name)

        # Create the zip file
        zip_path = build_dir / f"{FUNCTION_NAME}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(build_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(build_dir))
                    zipf.write(file_path, arcname)

        logger.info(f"Created zip file: {zip_path}")
        return str(zip_path)

    except Exception as e:
        logger.error(f"Error creating zip file: {str(e)}")
        raise


def wait_for_lambda_active(lambda_client, function_name: str):
    """Wait for the Lambda function to be active."""
    import time

    max_attempts = 10
    for _ in range(max_attempts):
        try:
            response = lambda_client.get_function_configuration(FunctionName=function_name)
            if response["State"] == "Active":
                logger.info("Lambda function is now active")
                return True
            logger.info("Waiting for Lambda function to be active...")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Waiting for Lambda function: {str(e)}")
            time.sleep(2)
    raise Exception("Timed out waiting for Lambda function to become active")


def deploy_lambda(zip_path: str):
    """Deploy the Lambda function to LocalStack."""
    try:
        lambda_client = boto3.client("lambda", **aws_config)

        role_arn = "arn:aws:iam::000000000000:role/lambda-role"  # Placeholder role for LocalStack

        # Read the zip file
        with open(zip_path, "rb") as f:
            zip_bytes = f.read()

        # Environment variables for the Lambda function
        environment = {
            "Variables": {
                "AWS_DEFAULT_REGION": AWS_REGION,
                "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
                "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
                "OPENSEARCH_URL": OPENSEARCH_URL,
                "SQS_QUEUE_URL": SQS_QUEUE_URL,
                "INDEX_NAME": INDEX_NAME,
                "PYTHONPATH": "/var/task:/opt/python",
            }
        }

        try:
            # Try to update the function if it exists
            response = lambda_client.update_function_code(FunctionName=FUNCTION_NAME, ZipFile=zip_bytes)
            # Update configuration
            lambda_client.update_function_configuration(
                FunctionName=FUNCTION_NAME,
                Runtime="python3.9",
                Role=role_arn,
                Handler="handler.lambda_handler",
                Timeout=30,
                MemorySize=256,
                Environment=environment,
            )
            logger.info(f"Updated Lambda function: {response['FunctionArn']}")
        except lambda_client.exceptions.ResourceNotFoundException:
            # Create the function if it doesn't exist
            response = lambda_client.create_function(
                FunctionName=FUNCTION_NAME,
                Runtime="python3.9",
                Role=role_arn,
                Handler="handler.lambda_handler",
                Code={"ZipFile": zip_bytes},
                Timeout=30,
                MemorySize=256,
                Environment=environment,
                Publish=True,
            )
            logger.info(f"Created Lambda function: {response['FunctionArn']}")

            # Wait for the function to be active
            wait_for_lambda_active(lambda_client, FUNCTION_NAME)
        except lambda_client.exceptions.ResourceConflictException:
            logger.info("Event source mapping already exists")
            return lambda_client

        return lambda_client
    except Exception as e:
        logger.error(f"Error deploying Lambda function: {str(e)}")
        raise


def ensure_sqs_queue_exists():
    """Ensure SQS queue exists, create it if it doesn't."""
    try:
        sqs = boto3.client("sqs", **aws_config)

        # Extract queue name from URL
        parsed_url = urlparse(SQS_QUEUE_URL)
        queue_name = parsed_url.path.split("/")[-1]

        try:
            # Try to get the queue URL to check if it exists
            sqs.get_queue_url(QueueName=queue_name)
            logger.info(f"SQS queue {queue_name} already exists")
            return sqs
        except sqs.exceptions.QueueDoesNotExist:
            # Create the queue if it doesn't exist
            logger.info(f"Creating SQS queue: {queue_name}")
            attributes = {"VisibilityTimeout": "300", "MessageRetentionPeriod": "1209600"}  # 5 minutes  # 14 days
            response = sqs.create_queue(QueueName=queue_name, Attributes=attributes)
            logger.info(f"Created SQS queue: {response['QueueUrl']}")

    except Exception as e:
        logger.error(f"Error ensuring SQS queue exists: {str(e)}")
        raise


def create_event_source_mapping(lambda_client):
    """Create SQS event source mapping for the Lambda function."""
    try:
        # First ensure the queue exists
        ensure_sqs_queue_exists()

        # Get the queue ARN
        queue_url = SQS_QUEUE_URL
        parsed_url = urlparse(queue_url)
        queue_name = parsed_url.path.split("/")[-1]
        # LocalStack ARN format: arn:aws:sqs:<region>:<account-id>:<queue-name>
        # For LocalStack, we use the default account ID '000000000000'
        queue_arn = f"arn:aws:sqs:ap-northeast-1:000000000000:{queue_name}"

        # Create event source mapping with required parameters for SQS
        try:
            response = lambda_client.create_event_source_mapping(
                EventSourceArn=queue_arn,
                FunctionName=FUNCTION_NAME,  # Must match the deployed Lambda function name
                Enabled=True,
                BatchSize=10,
                MaximumBatchingWindowInSeconds=0,  # Process messages as soon as they're available
                FunctionResponseTypes=["ReportBatchItemFailures"],  # Enable reporting batch item failures
            )
            logger.info(f"Created event source mapping: {response['UUID']}")
            return response
        except lambda_client.exceptions.InvalidParameterValueException as e:
            logger.error(f"Invalid parameters for event source mapping: {str(e)}")
            # Try to list existing event source mappings to help with debugging
            try:
                mappings = lambda_client.list_event_source_mappings(
                    FunctionName=FUNCTION_NAME, EventSourceArn=queue_arn
                )
                if mappings.get("EventSourceMappings"):
                    logger.info(f"Existing event source mappings: {mappings}")
            except Exception as list_error:
                logger.error(f"Failed to list event source mappings: {str(list_error)}")
            raise
        except lambda_client.exceptions.ResourceConflictException as e:
            logger.info(f"Event source mapping already exists: {str(e)}")

    except Exception as e:
        logger.error(f"Error creating event source mapping: {str(e)}")
        raise


def main():
    """Main deployment function."""
    try:
        # First ensure SQS queue exists
        ensure_sqs_queue_exists()

        # Create the deployment package
        zip_path = create_zip()

        # Deploy the Lambda function
        lambda_client = deploy_lambda(zip_path)

        # Create the event source mapping
        create_event_source_mapping(lambda_client)

        logger.info("Deployment completed successfully!")

    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
