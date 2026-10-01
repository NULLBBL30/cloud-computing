import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from tablestore import OTSServiceError

from app import alicloud_handlers


class FakeOtsClient:
    """In-memory Tablestore substitute with atomic conditional row inserts."""

    def __init__(self):
        self.rows = {}
        self._lock = threading.RLock()
        self.fail_next_event_write = False
        self.lose_next_event_write_response = False

    @staticmethod
    def _pairs(row, field):
        return {name: value for name, value, *_ in getattr(row, field)}

    def put_row(self, _table, row, _condition):
        primary_key = self._pairs(row, "primary_key")
        key = (primary_key["PK"], primary_key["SK"])
        with self._lock:
            if key in self.rows:
                raise OTSServiceError(403, "OTSConditionCheckFail", "duplicate row")
            if self.fail_next_event_write:
                self.fail_next_event_write = False
                raise RuntimeError("injected event write failure")
            self.rows[key] = self._pairs(row, "attribute_columns")
            if self.lose_next_event_write_response:
                self.lose_next_event_write_response = False
                raise TimeoutError("injected lost event write response")

    def get_row(self, _table, primary_key, *_args):
        key = tuple(value for _, value in primary_key)
        attributes = self.rows.get(key)
        if attributes is None:
            return None, None, None
        row = type("StoredRow", (), {"attribute_columns": [(name, value) for name, value in attributes.items()]})()
        return None, row, None

    def get_range(self, _table, _direction, start_key, _end_key, **_kwargs):
        partition = dict(start_key)["PK"]
        rows = []
        for (pk, sk), attributes in sorted(self.rows.items()):
            if pk == partition:
                row = type("StoredRow", (), {"attribute_columns": list(attributes.items())})()
                rows.append(row)
        return None, None, rows, None


@pytest.fixture()
def handler(monkeypatch):
    client = FakeOtsClient()
    monkeypatch.setenv("TENANT_KEYS", '{"key-a":"tenant-a","key-b":"tenant-b"}')
    monkeypatch.setenv("OTS_TABLE", "inventory")
    monkeypatch.setattr(alicloud_handlers, "_ots", lambda: client)
    return alicloud_handlers.http_handler


@pytest.fixture()
def ots_client(monkeypatch):
    client = FakeOtsClient()
    monkeypatch.setenv("TENANT_KEYS", '{"key-a":"tenant-a","key-b":"tenant-b"}')
    monkeypatch.setenv("OTS_TABLE", "inventory")
    monkeypatch.setattr(alicloud_handlers, "_ots", lambda: client)
    return client


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


def test_failed_event_write_leaves_no_partial_inventory_change_and_can_retry(ots_client):
    ots_client.fail_next_event_write = True
    payload = event("retry-after-failure")

    with pytest.raises(RuntimeError, match="injected event write failure"):
        alicloud_handlers._apply_inventory_event("tenant-a", payload)

    assert ots_client.rows == {}
    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "processed"
    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "duplicate ignored"
    assert alicloud_handlers._get_inventory("tenant-a", "sku-1") == (5, True)


def test_retry_after_lost_write_response_does_not_apply_twice(ots_client):
    ots_client.lose_next_event_write_response = True
    payload = event("commit-response-lost")

    with pytest.raises(TimeoutError, match="injected lost event write response"):
        alicloud_handlers._apply_inventory_event("tenant-a", payload)

    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "duplicate ignored"
    assert alicloud_handlers._get_inventory("tenant-a", "sku-1") == (5, True)


def test_concurrent_distinct_events_all_contribute_to_inventory(ots_client):
    payloads = [event(f"concurrent-{index}") for index in range(12)]

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda item: alicloud_handlers._apply_inventory_event("tenant-a", item), payloads))

    assert results == ["processed"] * len(payloads)
    assert alicloud_handlers._get_inventory("tenant-a", "sku-1") == (5 * len(payloads), True)


def test_concurrent_duplicate_event_is_applied_once(ots_client):
    payloads = [event("same-concurrent-event") for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda item: alicloud_handlers._apply_inventory_event("tenant-a", item), payloads))

    assert results.count("processed") == 1
    assert results.count("duplicate ignored") == len(payloads) - 1
    assert alicloud_handlers._get_inventory("tenant-a", "sku-1") == (5, True)


def test_event_ledger_adds_to_legacy_product_snapshot(ots_client):
    ots_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")] = {"quantity": 21}
    ots_client.rows[("TENANT#tenant-a", "EVENT#old-event")] = {
        "event_id": "old-event",
        "product_id": "sku-1",
    }

    assert alicloud_handlers._apply_inventory_event("tenant-a", event("new-event")) == "processed"

    assert alicloud_handlers._get_inventory("tenant-a", "sku-1") == (26, True)


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
