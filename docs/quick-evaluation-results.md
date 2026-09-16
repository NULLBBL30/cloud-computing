# Short baseline evaluation results

## Test scope

This is one short baseline run for each profile, executed on 2026-09-16 against the deployed Function Compute endpoint in `cn-hangzhou` at commit `38a97f1`. Each profile ran for one minute. The raw Locust CSV files remain in `data/raw/load/20260916-123355-*`; the generated summary is `data/derived/load-summary.csv`.

These results provide live-deployment evidence. They are not a substitute for the three repeated five to ten minute runs required by the final evaluation plan.

| Profile | Approximate achieved requests per second | Endpoint | Requests | Failures | p50 ms | p95 ms | p99 ms |
|---|---:|---|---:|---:|---:|---:|---:|
| Idle | 0.87 | POST `/events` | 41 | 0 | 130 | 270 | 300 |
| Idle | 0.87 | GET `/inventory/{product_id}` | 11 | 0 | 86 | 160 | 160 |
| Low | 8.38 | POST `/events` | 393 | 0 | 93 | 140 | 240 |
| Low | 8.38 | GET `/inventory/{product_id}` | 110 | 0 | 73 | 88 | 180 |
| Target | 41.88 | POST `/events` | 2015 | 0 | 90 | 110 | 160 |
| Target | 41.88 | GET `/inventory/{product_id}` | 498 | 0 | 71 | 92 | 1200 |
| High | 83.93 | POST `/events` | 4071 | 0 | 88 | 110 | 170 |
| High | 83.93 | GET `/inventory/{product_id}` | 965 | 0 | 70 | 87 | 150 |
| Stress | 125.97 | POST `/events` | 6080 | 0 | 88 | 110 | 170 |
| Stress | 125.97 | GET `/inventory/{product_id}` | 1478 | 0 | 70 | 88 | 150 |

## Initial interpretation

The one-minute baseline produced zero HTTP failures at every tested profile. Event writes stayed below the target p95 latency budget of 250 ms in this run. Inventory reads showed one 1200 ms p99 outlier in the target profile, so the final report must retain that value and investigate repeated-run variance rather than claim that every latency objective passed.

The 150-user profile achieved approximately 126 requests per second, lower than the nominal user count because each simulated user waits one second after a completed request. The report will therefore use observed request rate from the Locust CSV, not user count, when comparing results with NFR targets.
