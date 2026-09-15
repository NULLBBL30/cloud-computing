# Non Functional Requirements

| Dimension | Launch target | 100x planning target | Measurement |
|---|---:|---:|---|
| Availability | 99.9% monthly API availability | 99.9% | CloudWatch/API checks; downtime is failed health or event submission |
| Latency | p50/p95/p99 < 100/250/500 ms at 50 RPS | Same budgets at 500 RPS | Locust percentile CSV |
| Scale | 10 tenants, 50 RPS, 100,000 events/month | 1,000 tenants, 5,000 RPS, 10m events/month | Load tests and capacity model |
| Tenancy | 0 successful cross-tenant reads/writes | 0 | Automated isolation tests |
| Durability | RPO < 5 min, RTO < 30 min | Same | DynamoDB point-in-time recovery and restore drill plan |
| Security | 100% authenticated API requests; no repository secrets | Same | API tests, secret scan and IAM review |
