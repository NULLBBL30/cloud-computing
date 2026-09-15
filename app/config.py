import json
import os


def setting(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def tenant_keys() -> dict[str, str]:
    raw = setting("TENANT_KEYS", '{"demo-key-a":"retailer-a","demo-key-b":"retailer-b"}')
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError("TENANT_KEYS must be valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeError("TENANT_KEYS must be a JSON object")
    return {str(key): str(tenant) for key, tenant in value.items()}
