"""Alibaba Cloud FC HTTP handler for the deployed platform."""
import base64
import json
import os
from typing import Any
from urllib.parse import parse_qs

from tablestore import (
    INF_MAX,
    INF_MIN,
    OTSClient,
    OTSServiceError,
    Condition,
    Row,
    RowExistenceExpectation,
)

from app.config import tenant_keys
from app.models import InventoryEvent


def _body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body") or event.get("bodyString")
    if body is None and event.get("wsgi.input") is not None:
        body = event["wsgi.input"].read()
    body = body or "{}"
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, bytes):
        body = body.decode("utf-8")
    return json.loads(body) if isinstance(body, str) else body


def _response(code: int, payload: dict[str, Any], start_response: Any = None) -> str:
    """Serialize the payload for the FC Python HTTP-trigger handler.

    This runtime expects the handler return value itself to be the HTTP body;
    returning a Python dict serializes only its keys (``statusCodeheadersbody``).
    """
    if callable(start_response):
        reason = {200: "OK", 401: "Unauthorized", 404: "Not Found", 422: "Unprocessable Entity"}.get(code, "OK")
        start_response(f"{code} {reason}", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, x-api-key"),
        ])
    return json.dumps(payload)


def _dashboard(start_response: Any = None) -> str:
    """Return the same-origin browser console bundled with the FC package."""
    if callable(start_response):
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
    with open(os.path.join(os.path.dirname(__file__), "dashboard.html"), encoding="utf-8") as page:
        return page.read()


def _tenant(event: dict[str, Any]) -> str | None:
    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    api_key = headers.get("x-api-key") or event.get("HTTP_X_API_KEY", "")
    return tenant_keys().get(api_key)


def _query_value(event: dict[str, Any], key: str) -> str | None:
    """Read query parameters from both legacy and v3 FC HTTP events."""
    query = (
        event.get("queryParameters")
        or event.get("queryStringParameters")
        or event.get("queries")
        or {}
    )
    value = query.get(key) if isinstance(query, dict) else None
    if value is None and event.get("QUERY_STRING"):
        value = parse_qs(event["QUERY_STRING"]).get(key, [None])[0]
    return str(value) if value is not None else None


def _ots() -> OTSClient:
    return OTSClient(os.environ["OTS_ENDPOINT"], os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"], os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"], os.environ["OTS_INSTANCE"])


def http_handler(event: Any, _context: Any) -> str:
    event = json.loads(event.decode("utf-8") if isinstance(event, bytes) else event) if not isinstance(event, dict) else event
    # FC HTTP triggers expose the route as ``requestURI``; API Gateway-style
    # events instead use ``rawPath`` or ``path``.
    request_http = event.get("requestContext", {}).get("http", {})
    # The FC HTTP event format differs between runtime revisions.  One field
    # can contain only the trigger root ("/") while another retains the
    # requested suffix, so select the first non-root candidate.
    path_candidates = (
        event.get("PATH_INFO"),
        event.get("fc.request_uri"),
        request_http.get("path"),
        event.get("rawPath"),
        event.get("path"),
        event.get("pathInfo"),
        event.get("requestURI"),
    )
    path = next((item for item in path_candidates if item and item != "/"), "/")
    method = (event.get("REQUEST_METHOD") or request_http.get("method") or event.get("httpMethod") or "GET").upper()
    if method == "OPTIONS":
        return _response(200, {}, _context)
    tenant = _tenant(event)
    # This FC trigger forwards the request to the function root.  Preserve a
    # normal unauthenticated health probe even when its suffix is not exposed
    # in the event payload.
    if method == "GET" and path == "/":
        return _dashboard(_context)
    if path == "/health":
        return _response(200, {"status": "ok", "provider": "alicloud"}, _context)
    if not tenant:
        return _response(401, {"detail": "Invalid API key"}, _context)
    if method == "POST" and path in ("/events", "/"):
        try:
            inventory_event = InventoryEvent.model_validate(_body(event))
        except Exception as exc:
            return _response(422, {"detail": str(exc)}, _context)
        result = _apply_inventory_event(tenant, inventory_event.model_dump(mode="json"))
        return _response(200, {"status": result, "event_id": inventory_event.event_id}, _context)
    if method == "GET" and (path.startswith("/inventory/") or _query_value(event, "product_id")):
        product_id = _query_value(event, "product_id") or path.rsplit("/", 1)[-1]
        quantity, found = _get_inventory(tenant, product_id)
        if not found:
            return _response(404, {"detail": "inventory item not found"}, _context)
        return _response(200, {"tenant_id": tenant, "product_id": product_id, "quantity": quantity}, _context)
    return _response(404, {"detail": "not found"}, _context)


def _apply_inventory_event(tenant: str, inventory_event: dict[str, Any]) -> str:
    """Append one idempotent inventory event; this is the only write."""
    event_id = inventory_event["event_id"]
    pk = f"TENANT#{tenant}"
    table = os.environ["OTS_TABLE"]
    client = _ots()
    try:
        event_key = [("PK", pk), ("SK", f"EVENT#{event_id}")]
        client.put_row(
            table,
            Row(
                event_key,
                [
                    ("event_id", event_id),
                    ("store_id", inventory_event["store_id"]),
                    ("product_id", inventory_event["product_id"]),
                    ("event_type", inventory_event["event_type"]),
                    ("quantity", int(inventory_event["quantity"])),
                    ("quantity_delta", _event_delta(inventory_event)),
                ],
            ),
            Condition(RowExistenceExpectation.EXPECT_NOT_EXIST),
        )
        return "processed"
    except OTSServiceError as exc:
        if exc.get_error_code() == "OTSConditionCheckFail":
            return "duplicate ignored"
        raise


def _event_delta(inventory_event: dict[str, Any]) -> int:
    quantity = int(inventory_event["quantity"])
    return -quantity if inventory_event["event_type"] == "SALE" else quantity


def _get_inventory(tenant: str, product_id: str) -> tuple[int, bool]:
    """Sum append-only events over the legacy quantity as a migration baseline.

    Existing PRODUCT rows are retained as opening balances. Older EVENT rows
    lack quantity_delta and are ignored because their effects are already
    included in those balances.
    """
    client = _ots()
    table = os.environ["OTS_TABLE"]
    pk = f"TENANT#{tenant}"
    _, base_row, _ = client.get_row(
        table,
        [("PK", pk), ("SK", f"PRODUCT#{product_id}")],
        None,
        None,
        1,
    )
    base_attributes = {} if base_row is None else {
        name: value for name, value, *_ in base_row.attribute_columns
    }
    quantity = int(base_attributes.get("quantity", 0))
    found = base_row is not None

    start_key = [("PK", pk), ("SK", INF_MIN)]
    end_key = [("PK", pk), ("SK", INF_MAX)]
    while start_key is not None:
        _, next_start, rows, _ = client.get_range(
            table,
            "FORWARD",
            start_key,
            end_key,
            columns_to_get=["product_id", "quantity_delta"],
            limit=1000,
        )
        for row in rows:
            attributes = {name: value for name, value, *_ in row.attribute_columns}
            if attributes.get("product_id") != product_id or "quantity_delta" not in attributes:
                continue
            quantity += int(attributes["quantity_delta"])
            found = True
        start_key = next_start

    return quantity, found
