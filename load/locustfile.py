from locust import HttpUser, constant, task
import uuid


class RetailStoreUser(HttpUser):
    # One user issues approximately one request per second.  The evaluation
    # script varies user count so the profiles are easy to reproduce.
    wait_time = constant(1)
    headers = {"X-API-Key": "demo-key-a"}

    @task(4)
    def submit_stock_event(self):
        self.client.post(
            "/events",
            name="POST /events",
            headers=self.headers,
            json={
                "event_id": f"load-{uuid.uuid4()}",
                "store_id": "load-store-01",
                "product_id": "load-sku-001",
                "event_type": "STOCK_RECEIVED",
                "quantity": 1,
            },
        )

    @task(1)
    def read_inventory(self):
        self.client.get("/inventory/load-sku-001", name="GET /inventory/{product_id}", headers=self.headers)
