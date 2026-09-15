import json
import logging
from fastapi import Depends, FastAPI, HTTPException, status
from botocore.exceptions import ClientError

from app.auth import current_tenant
from app.aws import bootstrap_resources, cloudwatch, dynamodb, queue_url, sqs, table_name
from app.models import InventoryEvent, InventoryResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("inventory-api")
app = FastAPI(title="Multi-tenant Inventory Event Platform", version="0.1.0")


def metric(name: str, value: float) -> None:
    try:
        cloudwatch().put_metric_data(Namespace="InventoryPlatform", MetricData=[{"MetricName": name, "Value": value, "Unit": "Count"}])
    except Exception:  # metrics must not break the customer journey
        logger.warning("metric emission failed", exc_info=True)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        bootstrap_resources()
        return {"status": "ok"}
    except Exception as exc:
        logger.exception("health check failed")
        raise HTTPException(status_code=503, detail="dependency unavailable") from exc


@app.post("/events", status_code=status.HTTP_202_ACCEPTED)
def submit_event(event: InventoryEvent, tenant: str = Depends(current_tenant)) -> dict[str, str]:
    envelope = {"tenant_id": tenant, **event.model_dump(mode="json")}
    try:
        sqs().send_message(QueueUrl=queue_url(), MessageBody=json.dumps(envelope))
        metric("EventsAccepted", 1)
        logger.info("event accepted tenant=%s event_id=%s", tenant, event.event_id)
        return {"status": "accepted", "event_id": event.event_id}
    except ClientError as exc:
        logger.exception("queue unavailable")
        raise HTTPException(status_code=503, detail="event queue unavailable") from exc


@app.get("/inventory/{product_id}", response_model=InventoryResponse)
def get_inventory(product_id: str, tenant: str = Depends(current_tenant)) -> InventoryResponse:
    response = dynamodb().get_item(TableName=table_name(), Key={"PK": {"S": f"TENANT#{tenant}"}, "SK": {"S": f"PRODUCT#{product_id}"}}, ConsistentRead=True)
    item = response.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="inventory item not found")
    return InventoryResponse(tenant_id=tenant, product_id=product_id, quantity=int(item["quantity"]["N"]))
