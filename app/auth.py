from fastapi import Header, HTTPException, status
from app.config import tenant_keys


def current_tenant(x_api_key: str | None = Header(default=None)) -> str:
    tenant = tenant_keys().get(x_api_key or "")
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return tenant
