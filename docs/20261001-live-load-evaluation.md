# Live load evaluation — 2026-10-01

The event-ledger deployment was tested at the public Function Compute endpoint after the green deployment workflow and live API smoke checks. The Locust workload uses a 4:1 event-write/read task mix, one shared tenant, unique event IDs, and `load-sku-001`.

| Load level | Duration | Requests/s | Total failures | GET average | GET p95 / p99 | Outcome |
|---|---:|---:|---:|---:|---:|---|
| 1 user | 5 min | 0.91 | 0 | 136 ms | 150 / 210 ms | Completed |
| 10 users | 5 min | 8.98 | 0 | 161 ms | 220 / 240 ms | Completed |
| 50 users | 10 min | 42.63 | 5 (0.02%) | 511 ms | 860 / 980 ms | Completed; first 502s appeared |
| 100 users | 9.2 min, stopped early | 69.42 | 691 (1.81%) | 1,744 ms | 3,500 / 3,700 ms | Stopped at about 9.1% GET failures |
| 150 users | 45 sec, stopped early | 68.99 | 470 (17.81%) | 3,421 ms | 3,700 / 3,800 ms | Stopped at about 87.7% GET failures |

Failures were HTTP 502 responses and concentrated in `GET /inventory/{product_id}`. POST event writes remained almost entirely successful through 100 users. The observed trend is consistent with the append-only read path scanning an increasingly large tenant partition: GET latency and failures rose while writes stayed fast. This is the first measured degradation point for the current event volume; the 100- and 150-user results are short, stopped samples and are not comparable to complete 10-minute runs.

The 150-user sample was stopped as soon as the GET failure rate exceeded 80%. After load ended, `/health` returned HTTP 200 and a read of `load-sku-001` returned HTTP 200 with quantity `62809`. This confirms both health and inventory reads recovered after load.

Raw Locust CSV and run metadata are in `data/raw/load/20261001-164212-{idle,low,target,high,stress-sentinel}/`. The 100-user and 150-user metadata record their early-stop reasons. `data/derived/load-summary.csv` contains the corresponding endpoint summaries plus the existing historical runs.

## Limits and remaining evidence

- The 100-user and 150-user profiles stopped early after substantial 502 rates; do not present them as full-duration benchmarks.
- The three-run repeat requirement remains outstanding.
- Scaling latency and FC instance/concurrency graphs were not captured; obtain them from CloudMonitor after selecting an active contact group and running the controlled 10-to-100 user ramp.
- CloudMonitor alarm and notification evidence remains pending. Follow `docs/cloudmonitor-setup.md`.
- The Tablestore dependency-outage experiment remains pending and must use an isolated test version.
