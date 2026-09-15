import os
import time
import boto3
from botocore.exceptions import ClientError

from app.config import setting


def _kwargs() -> dict:
    endpoint = setting("MOTO_ENDPOINT")
    return {"region_name": setting("AWS_REGION", "us-east-1"), **({"endpoint_url": endpoint} if endpoint else {})}


def dynamodb():
    return boto3.client("dynamodb", **_kwargs())


def sqs():
    return boto3.client("sqs", **_kwargs())


def cloudwatch():
    return boto3.client("cloudwatch", **_kwargs())


def table_name() -> str:
    return str(setting("INVENTORY_TABLE", "inventory-platform"))


def queue_name() -> str:
    return str(setting("EVENT_QUEUE", "inventory-events"))


def queue_url() -> str:
    return sqs().get_queue_url(QueueName=queue_name())["QueueUrl"]


def bootstrap_resources(wait_seconds: int = 15) -> None:
    """Idempotently creates moto resources for local deployment and tests."""
    db = dynamodb()
    try:
        db.describe_table(TableName=table_name())
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ResourceNotFoundException":
            raise
        db.create_table(
            TableName=table_name(),
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        )
        for _ in range(wait_seconds * 10):
            if db.describe_table(TableName=table_name())["Table"]["TableStatus"] == "ACTIVE":
                break
            time.sleep(0.1)
    client = sqs()
    try:
        client.get_queue_url(QueueName=queue_name())
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "AWS.SimpleQueueService.NonExistentQueue":
            raise
        client.create_queue(QueueName=queue_name(), Attributes={"VisibilityTimeout": "30"})
