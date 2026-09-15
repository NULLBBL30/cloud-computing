import json
from app.aws import queue_url, sqs
from worker.worker import process


def event(event_id: str = "e-1"):
    return {"event_id": event_id, "store_id": "dublin-1", "product_id": "phone-1", "event_type": "STOCK_RECEIVED", "quantity": 5}


def process_one() -> None:
    message = sqs().receive_message(QueueUrl=queue_url(), MaxNumberOfMessages=1)["Messages"][0]
    process(message)
    sqs().delete_message(QueueUrl=queue_url(), ReceiptHandle=message["ReceiptHandle"])


def test_tenant_isolation(client):
    assert client.post("/events", headers={"X-API-Key": "key-a"}, json=event()).status_code == 202
    process_one()
    assert client.get("/inventory/phone-1", headers={"X-API-Key": "key-a"}).json()["quantity"] == 5
    assert client.get("/inventory/phone-1", headers={"X-API-Key": "key-b"}).status_code == 404


def test_duplicate_event_is_idempotent(client):
    payload = event("same-event")
    for _ in range(2):
        client.post("/events", headers={"X-API-Key": "key-a"}, json=payload)
        process_one()
    assert client.get("/inventory/phone-1", headers={"X-API-Key": "key-a"}).json()["quantity"] == 5
