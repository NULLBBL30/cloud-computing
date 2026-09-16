"""Alibaba Cloud FC HTTP handler for the deployed platform."""
import base64
import json
import os
from typing import Any
from urllib.parse import parse_qs

from tablestore import OTSClient, Condition, Row, RowExistenceExpectation

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
        _, row, _ = _ots().get_row(os.environ["OTS_TABLE"], [("PK", f"TENANT#{tenant}"), ("SK", f"PRODUCT#{product_id}")], None, None, 1)
        if row is None:
            return _response(404, {"detail": "inventory item not found"}, _context)
        values = dict((name, value) for name, value, *_ in row.attribute_columns)
        return _response(200, {"tenant_id": tenant, "product_id": product_id, "quantity": int(values.get("quantity", 0))}, _context)
    return _response(404, {"detail": "not found"}, _context)


def _apply_inventory_event(tenant: str, inventory_event: dict[str, Any]) -> str:
    """Apply an idempotent inventory event in the request path."""
    event_id = inventory_event["event_id"]
    pk = f"TENANT#{tenant}"
    table = os.environ["OTS_TABLE"]
    client = _ots()
    try:
        client.put_row(table, Row([("PK", pk), ("SK", f"EVENT#{event_id}")], [("event_id", event_id), ("store_id", inventory_event["store_id"])]), Condition(RowExistenceExpectation.EXPECT_NOT_EXIST))
    except Exception:
        return "duplicate ignored"
    product = inventory_event["product_id"]
    delta = -int(inventory_event["quantity"]) if inventory_event["event_type"] == "SALE" else int(inventory_event["quantity"])
    _, row, _ = client.get_row(table, [("PK", pk), ("SK", f"PRODUCT#{product}")], None, None, 1)
    values = {} if row is None else dict((name, value) for name, value, *_ in row.attribute_columns)
    client.put_row(table, Row([("PK", pk), ("SK", f"PRODUCT#{product}")], [("quantity", int(values.get("quantity", 0)) + delta), ("store_id", inventory_event["store_id"]), ("updated_event_id", event_id)]), Condition(RowExistenceExpectation.IGNORE))
    return "processed"
