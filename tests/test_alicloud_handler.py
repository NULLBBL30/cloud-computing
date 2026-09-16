import json

import pytest
from tablestore import OTSServiceError

from app import alicloud_handlers


class FakeOtsClient:
    """Small in-memory substitute used only to test the FC handler contract."""

    def __init__(self):
        self.rows = {}

    @staticmethod
    def _pairs(row, field):
        return {name: value for name, value, *_ in getattr(row, field)}

    def put_row(self, _table, row, _condition):
        primary_key = self._pairs(row, "primary_key")
        key = (primary_key["PK"], primary_key["SK"])
        if key[1].startswith("EVENT#") and key in self.rows:
            raise OTSServiceError(403, "OTSConditionCheckFail", "duplicate event")
        self.rows[key] = self._pairs(row, "attribute_columns")

    def get_row(self, _table, primary_key, *_args):
        key = tuple(value for _, value in primary_key)
        attributes = self.rows.get(key)
        if attributes is None:
            return None, None, None
        row = type("StoredRow", (), {"attribute_columns": [(name, value) for name, value in attributes.items()]})()
        return None, row, None


@pytest.fixture()
def handler(monkeypatch):
    client = FakeOtsClient()
    monkeypatch.setenv("TENANT_KEYS", '{"key-a":"tenant-a","key-b":"tenant-b"}')
    monkeypatch.setenv("OTS_TABLE", "inventory")
    monkeypatch.setattr(alicloud_handlers, "_ots", lambda: client)
    return alicloud_handlers.http_handler


def request(method, path, api_key=None, body=None):
    return {
        "REQUEST_METHOD": method,
        "path": path,
        "headers": {} if api_key is None else {"x-api-key": api_key},
        "body": json.dumps(body or {}),
    }


def event(event_id="event-1"):
    return {
        "event_id": event_id,
        "store_id": "store-1",
        "product_id": "sku-1",
        "event_type": "STOCK_RECEIVED",
        "quantity": 5,
    }


def test_tenant_isolation(handler):
    assert json.loads(handler(request("POST", "/events", "key-a", event()), None))["status"] == "processed"
    tenant_a = json.loads(handler(request("GET", "/inventory/sku-1", "key-a"), None))
    tenant_b = json.loads(handler(request("GET", "/inventory/sku-1", "key-b"), None))
    assert tenant_a == {"tenant_id": "tenant-a", "product_id": "sku-1", "quantity": 5}
    assert tenant_b == {"detail": "inventory item not found"}


def test_duplicate_event_is_idempotent(handler):
    assert json.loads(handler(request("POST", "/events", "key-a", event("same-event")), None))["status"] == "processed"
    assert json.loads(handler(request("POST", "/events", "key-a", event("same-event")), None))["status"] == "duplicate ignored"
    inventory = json.loads(handler(request("GET", "/inventory/sku-1", "key-a"), None))
    assert inventory["quantity"] == 5


def test_rejects_invalid_api_key(handler):
    assert json.loads(handler(request("POST", "/events", "wrong-key", event()), None)) == {"detail": "Invalid API key"}


def test_options_includes_browser_headers(handler):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    assert json.loads(handler(request("OPTIONS", "/events"), start_response)) == {}
    assert captured["status"] == "200 OK"
    assert captured["headers"]["Access-Control-Allow-Origin"] == "*"
    assert "OPTIONS" in captured["headers"]["Access-Control-Allow-Methods"]
