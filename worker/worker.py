import json
import logging
import time
from botocore.exceptions import ClientError

from app.aws import bootstrap_resources, cloudwatch, dynamodb, queue_url, sqs, table_name

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("inventory-worker")


def delta(event_type: str, quantity: int) -> int:
    return -quantity if event_type == "SALE" else quantity


def process_event(event: dict) -> bool:
    tenant, event_id, product_id = event["tenant_id"], event["event_id"], event["product_id"]
    pk = f"TENANT#{tenant}"
    try:
        dynamodb().put_item(
            TableName=table_name(), Item={"PK": {"S": pk}, "SK": {"S": f"EVENT#{event_id}"}},
            ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)",
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.info("duplicate ignored tenant=%s event_id=%s", tenant, event_id)
            return True
        raise
    dynamodb().update_item(
        TableName=table_name(), Key={"PK": {"S": pk}, "SK": {"S": f"PRODUCT#{product_id}"}},
        UpdateExpression="ADD quantity :change SET updated_at = :event_id",
        ExpressionAttributeValues={":change": {"N": str(delta(event["event_type"], int(event["quantity"])))}, ":event_id": {"S": event_id}},
    )
    cloudwatch().put_metric_data(Namespace="InventoryPlatform", MetricData=[{"MetricName": "EventsProcessed", "Value": 1, "Unit": "Count"}])
    logger.info("event processed tenant=%s event_id=%s", tenant, event_id)
    return True


def process(message: dict) -> bool:
    return process_event(json.loads(message["Body"]))


def run() -> None:
    bootstrap_resources()
    url = queue_url()
    while True:
        result = sqs().receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=10, VisibilityTimeout=30)
        for message in result.get("Messages", []):
            try:
                process(message)
                sqs().delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])
            except Exception:
                logger.exception("message processing failed")
        time.sleep(0.05)


if __name__ == "__main__":
    run()
