"""Alibaba Cloud FC handlers for the deployed platform.

Local FastAPI/moto remains for unit tests. FC uses these native HTTP and MNS
handlers, keeping cloud credentials in FC environment variables only.
"""
import base64
import json
import os
from typing import Any

from mns.account import Account
from mns.topic import TopicMessage
from tablestore import OTSClient, Condition, Row, RowExistenceExpectation

from app.config import tenant_keys
from app.models import InventoryEvent


def _body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or event.get("bodyString") or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    return json.loads(body) if isinstance(body, str) else body


def _response(code: int, payload: dict[str, Any]) -> str:
    """Serialize the payload for the FC Python HTTP-trigger handler.

    This runtime expects the handler return value itself to be the HTTP body;
    returning a Python dict serializes only its keys (``statusCodeheadersbody``).
    """
    del code  # FC's legacy Python HTTP trigger always emits the returned body.
    return json.dumps(payload)


def _tenant(event: dict[str, Any]) -> str | None:
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    return tenant_keys().get(headers.get("x-api-key", ""))


def _mns_topic():
    endpoint = os.environ["MNS_ENDPOINT"]
    account = Account(endpoint, os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"], os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"])
    return account.get_topic_ref(os.environ["MNS_TOPIC"])


def _ots() -> OTSClient:
    return OTSClient(os.environ["OTS_ENDPOINT"], os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"], os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"], os.environ["OTS_INSTANCE"])


def http_handler(event: Any, _context: Any) -> dict[str, Any]:
    event = json.loads(event.decode("utf-8") if isinstance(event, bytes) else event) if not isinstance(event, dict) else event
    path = event.get("rawPath") or event.get("path") or "/"
    method = (event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod") or "GET").upper()
    if path == "/health":
        return _response(200, {"status": "ok", "provider": "alicloud"})
    tenant = _tenant(event)
    if not tenant:
        return _response(401, {"detail": "Invalid API key"})
    if method == "POST" and path == "/events":
        try:
            inventory_event = InventoryEvent.model_validate(_body(event))
        except Exception as exc:
            return _response(422, {"detail": str(exc)})
        message = {"tenant_id": tenant, **inventory_event.model_dump(mode="json")}
        _mns_topic().publish_message(TopicMessage(json.dumps(message)))
        return _response(202, {"status": "accepted", "event_id": inventory_event.event_id})
    if method == "GET" and path.startswith("/inventory/"):
        product_id = path.rsplit("/", 1)[-1]
        _, row, _ = _ots().get_row(os.environ["OTS_TABLE"], [("PK", f"TENANT#{tenant}"), ("SK", f"PRODUCT#{product_id}")], None, 1)
        if row is None:
            return _response(404, {"detail": "inventory item not found"})
        values = dict((name, value) for name, value, *_ in row.attribute_columns)
        return _response(200, {"tenant_id": tenant, "product_id": product_id, "quantity": int(values.get("quantity", 0))})
    return _response(404, {"detail": "not found"})


def worker_handler(event: Any, _context: Any) -> str:
    event = json.loads(event.decode("utf-8") if isinstance(event, bytes) else event) if not isinstance(event, dict) else event
    data = event.get("data", event)
    payload = data.get("messageBody", data.get("body", data)) if isinstance(data, dict) else data
    inventory_event = json.loads(payload) if isinstance(payload, str) else payload
    tenant, event_id = inventory_event["tenant_id"], inventory_event["event_id"]
    pk = f"TENANT#{tenant}"
    table = os.environ["OTS_TABLE"]
    client = _ots()
    try:
        client.put_row(table, Row([("PK", pk), ("SK", f"EVENT#{event_id}")], [("event_id", event_id)]), Condition(RowExistenceExpectation.EXPECT_NOT_EXIST))
    except Exception:
        return "duplicate ignored"
    product = inventory_event["product_id"]
    delta = -int(inventory_event["quantity"]) if inventory_event["event_type"] == "SALE" else int(inventory_event["quantity"])
    _, row, _ = client.get_row(table, [("PK", pk), ("SK", f"PRODUCT#{product}")], None, 1)
    values = {} if row is None else dict((name, value) for name, value, *_ in row.attribute_columns)
    client.put_row(table, Row([("PK", pk), ("SK", f"PRODUCT#{product}")], [("quantity", int(values.get("quantity", 0)) + delta), ("updated_event_id", event_id)]), Condition(RowExistenceExpectation.IGNORE))
    return "processed"
