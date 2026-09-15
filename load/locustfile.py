from locust import HttpUser, between, task
import uuid


class RetailStoreUser(HttpUser):
    wait_time = between(0.01, 0.1)
    headers = {"X-API-Key": "demo-key-a"}

    @task(4)
    def submit_stock_event(self):
        self.client.post("/events", headers=self.headers, json={"event_id": str(uuid.uuid4()), "store_id": "dublin-1", "product_id": "phone-1", "event_type": "STOCK_RECEIVED", "quantity": 1})

    @task(1)
    def read_inventory(self):
        self.client.get("/inventory/phone-1", headers=self.headers)
