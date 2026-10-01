import json
import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from tablestore import OTSServiceError

from app import alicloud_handlers


class FakeOtsClient:
    """In-memory Tablestore substitute with atomic tenant-partition transactions."""

    def __init__(self):
        self.rows = {}
        self._lock = threading.RLock()
        self._transactions = {}
        self.fail_product_write = False
        self.lose_next_commit_response = False
        self.start_conflicts_remaining = 0
        self.start_calls = 0

    def start_local_transaction(self, _table, _partition_key):
        self.start_calls += 1
        if self.start_conflicts_remaining:
            self.start_conflicts_remaining -= 1
            raise OTSServiceError(409, "OTSRowOperationConflict", "partition is locked")
        self._lock.acquire()
        transaction_id = str(threading.get_ident())
        self._transactions[transaction_id] = deepcopy(self.rows)
        return transaction_id

    def commit_transaction(self, transaction_id):
        self.rows = self._transactions.pop(transaction_id)
        self._lock.release()
        if self.lose_next_commit_response:
            self.lose_next_commit_response = False
            raise TimeoutError("injected lost commit response")

    def abort_transaction(self, transaction_id):
        self._transactions.pop(transaction_id)
        self._lock.release()

    @staticmethod
    def _pairs(row, field):
        return {name: value for name, value, *_ in getattr(row, field)}

    def put_row(self, _table, row, _condition, transaction_id=None):
        primary_key = self._pairs(row, "primary_key")
        key = (primary_key["PK"], primary_key["SK"])
        rows = self._transactions[transaction_id] if transaction_id else self.rows
        if key[1].startswith("EVENT#") and key in rows:
            raise OTSServiceError(403, "OTSConditionCheckFail", "duplicate event")
        if key[1].startswith("PRODUCT#") and self.fail_product_write:
            self.fail_product_write = False
            raise RuntimeError("injected product write failure")
        rows[key] = self._pairs(row, "attribute_columns")

    def get_row(self, _table, primary_key, *_args, transaction_id=None):
        key = tuple(value for _, value in primary_key)
        rows = self._transactions[transaction_id] if transaction_id else self.rows
        attributes = rows.get(key)
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


@pytest.fixture()
def transactional_client(monkeypatch):
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


def test_failed_inventory_write_aborts_event_record_and_retry_applies_once(transactional_client):
    transactional_client.fail_product_write = True
    payload = event("retry-after-failure")

    with pytest.raises(RuntimeError, match="injected product write failure"):
        alicloud_handlers._apply_inventory_event("tenant-a", payload)

    assert transactional_client.rows == {}
    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "processed"
    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "duplicate ignored"
    product = transactional_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")]
    assert product["quantity"] == 5


def test_retry_after_lost_commit_response_does_not_apply_twice(transactional_client):
    transactional_client.lose_next_commit_response = True
    payload = event("commit-response-lost")

    with pytest.raises(TimeoutError, match="injected lost commit response"):
        alicloud_handlers._apply_inventory_event("tenant-a", payload)

    assert alicloud_handlers._apply_inventory_event("tenant-a", payload) == "duplicate ignored"
    product = transactional_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")]
    assert product["quantity"] == 5


def test_partition_lock_conflict_retries_before_writing(transactional_client):
    transactional_client.start_conflicts_remaining = 2

    assert alicloud_handlers._apply_inventory_event("tenant-a", event("after-lock-conflict")) == "processed"

    assert transactional_client.start_calls == 3
    assert transactional_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")]["quantity"] == 5


def test_concurrent_distinct_events_do_not_lose_inventory_updates(transactional_client):
    payloads = [event(f"concurrent-{index}") for index in range(12)]

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(lambda item: alicloud_handlers._apply_inventory_event("tenant-a", item), payloads))

    assert results == ["processed"] * len(payloads)
    product = transactional_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")]
    assert product["quantity"] == 5 * len(payloads)


def test_concurrent_duplicate_event_is_applied_once(transactional_client):
    payloads = [event("same-concurrent-event") for _ in range(8)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda item: alicloud_handlers._apply_inventory_event("tenant-a", item), payloads))

    assert results.count("processed") == 1
    assert results.count("duplicate ignored") == len(payloads) - 1
    product = transactional_client.rows[("TENANT#tenant-a", "PRODUCT#sku-1")]
    assert product["quantity"] == 5


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
