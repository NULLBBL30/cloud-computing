"""AWS Lambda entry points for the public API and SQS worker."""
import json
from mangum import Mangum
from app.main import app
from worker.worker import process_event

handler = Mangum(app, lifespan="off")


def sqs_worker_handler(event: dict, _context: object) -> dict:
    """Process each SQS record; failed records are retried by Lambda/SQS."""
    failures = []
    for record in event.get("Records", []):
        try:
            process_event(json.loads(record["body"]))
        except Exception:
            failures.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failures}
