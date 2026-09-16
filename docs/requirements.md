# Non Functional Requirements

| Dimension | Launch target | 100x planning target | Measurement |
|---|---:|---:|---|
| Availability | 99.9% monthly API availability | 99.9% | FC health checks; downtime is a failed health or event submission |
| Latency | p50/p95/p99 < 100/250/500 ms at 50 RPS | Same budgets at 500 RPS | Locust percentile CSV |
| Scale | 10 tenants, 50 RPS, 100,000 events/month | 1,000 tenants, 5,000 RPS, 10m events/month | Load tests and FC concurrency evidence |
| Tenancy | 0 successful cross-tenant reads/writes | 0 | API-key isolation tests using the same product ID for two tenants |
| Durability | RPO < 5 min, RTO < 30 min | Same | Tablestore backup/recovery plan and restore drill |
| Security | 100% authenticated inventory requests; no repository secrets | Same | API tests, secret scan and RAM review |

Tenant identity is derived only from the API key. Tablestore rows use `PK = TENANT#{tenant_id}` and `SK = PRODUCT#{product_id}`; `store_id` is retained as a business attribute and never authorizes access.
