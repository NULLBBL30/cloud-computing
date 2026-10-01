"""Fail deployment before Terraform changes if Tablestore transactions are unavailable."""
import os

from tablestore import OTSClient


region = os.environ.get("ALICLOUD_REGION", "cn-hangzhou")
instance = os.environ.get("OTS_INSTANCE", "invplatots")
table = os.environ.get("OTS_TABLE", "inventory")
endpoint = os.environ.get(
    "OTS_ENDPOINT",
    f"https://{instance}.{region}.ots.aliyuncs.com",
)
access_key = os.environ["ALICLOUD_ACCESS_KEY"]
access_secret = os.environ["ALICLOUD_SECRET_KEY"]

client = OTSClient(endpoint, access_key, access_secret, instance)
transaction_id = client.start_local_transaction(
    table,
    [("PK", "TENANT#ci-transaction-preflight")],
)
client.abort_transaction(transaction_id)
print(f"Tablestore local transactions are enabled for {instance}/{table}.")
