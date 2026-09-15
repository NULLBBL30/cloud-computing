import os
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("MOTO_ENDPOINT", raising=False)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("TENANT_KEYS", '{"key-a":"tenant-a","key-b":"tenant-b"}')
    with mock_aws():
        from app.aws import bootstrap_resources
        bootstrap_resources()
        from app.main import app
        yield TestClient(app)
