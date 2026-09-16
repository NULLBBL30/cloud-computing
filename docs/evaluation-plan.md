# Evaluation plan and evidence log

## Reproducible load protocol

Run each profile three times against the deployed API URL. `scripts/run-evaluation.ps1` creates timestamped CSV exports and `run-metadata.json` automatically. Record the Function Compute memory/concurrency configuration in the evidence log.

| Profile | Target rate | Duration | Purpose |
|---|---:|---:|---|
| Idle | 1 user, approximately 1 RPS | 5 min | Baseline and cold-start observation |
| Low | 10 users, approximately 10 RPS | 5 min | Establish baseline |
| Target | 50 users, approximately 50 RPS | 10 min | Check initial requirement |
| High | 100 users, approximately 100 RPS | 10 min | Observe burst behaviour |
| Stress | 150 users, approximately 150 RPS | 10 min | Identify bottleneck |

Report p50, p95, p99, throughput, error rate, FC concurrency/instance evidence and the observed bottleneck for every run. Do not report only mean latency.

## Scaling measurement

Function Compute scales HTTP-handler instances automatically as concurrent demand increases. Apply a controlled jump from 10 to 100 users and record spike start, first observed instance/concurrency increase, maximum concurrency and return-to-baseline time. Report scaling delay as the interval from spike start to the first sustained increase. Configure an alert on FC invocation errors or error rate.

## Failure protocol

At 50 RPS, deploy a temporary test configuration with the Tablestore table name set to `inventory-invalid-test` for 60 seconds. Record the HTTP error rate, latency, FC logs and alert response, then restore the correct table name and measure recovery time. Run this only against a controlled test version, not the presentation version.

## Raw evidence checklist

- `data/raw/load/`: Locust request/statistics CSV files.
- `data/raw/scaling/`: FC concurrency/instance exports with a timestamped spike timeline.
- `data/raw/failure/`: Locust CSV, FC logs, alert evidence and timeline CSV.
- `data/raw/cost/`: public-price source URL, price date, assumptions and calculation CSV.
- `analysis/`: scripts that transform raw data into figures and tables.

## Cost model template

Record price-source date and region before calculating. State every assumption: event volume, Tablestore read/write usage, log retention, Function Compute GB-seconds and OSS state storage.

| Metric | Formula |
|---|---|
| Monthly platform cost | Function Compute + Tablestore + OSS + logs/monitoring |
| Cost per tenant/month | Monthly platform cost / active tenants |
| Cost per 1,000 requests | Monthly platform cost / (monthly requests / 1,000) |
| 100x projection | Recalculate with 100x events, tenants and required concurrency |

Use current published prices on the date of calculation; do not reuse vendor or cloud price claims without a dated source.
