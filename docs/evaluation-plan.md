# Evaluation plan and evidence log

## Reproducible load protocol

Run each profile three times against the deployed API URL. Save unchanged Locust CSV exports under `data/raw/load/<profile>-run<n>/`. Record the cloud region, commit hash, Lambda memory/concurrency configuration and test date in `run-metadata.json`.

| Profile | Target rate | Duration | Purpose |
|---|---:|---:|---|
| Idle | 1 RPS | 5 min | Baseline and cold-start observation |
| Low | 10 RPS | 5 min | Establish baseline |
| Target | 50 RPS | 10 min | Check initial requirement |
| High | 100 RPS | 10 min | Observe burst behaviour |
| Stress | Step +25 RPS / 2 min | Until degradation | Identify bottleneck |

Report p50, p95, p99, throughput, error rate, SQS queue depth, Lambda concurrent executions and the observed bottleneck for every run. Do not report only mean latency.

## Scaling measurement

Lambda's SQS event-source mapping expands worker concurrency automatically, bounded at 20. Apply a controlled jump from 10 to 100 RPS and record spike start, first increase in Lambda `ConcurrentExecutions`, maximum concurrency, queue-depth peak and return-to-baseline time. Report scaling delay as the interval from spike start to the first sustained concurrency increase. The CloudWatch alarm remains an operational wake-up rule when queue depth exceeds 200 for one minute.

## Failure protocol

At 50 RPS, temporarily disable the SQS event-source mapping or set its Lambda reserved concurrency to zero for 60 seconds. The API should continue returning `202` while the SQS visible-message count increases. Restore the mapping and measure the time until the queue returns to zero. Report user-visible impact: event acceptance remains available, but inventory reads may be stale until recovery.

## Raw evidence checklist

- `data/raw/load/`: Locust request/statistics CSV files.
- `data/raw/scaling/`: CloudWatch concurrency and queue-depth exports with a timestamped spike timeline.
- `data/raw/failure/`: Locust CSV, queue-depth samples, CloudWatch/Lambda logs and timeline CSV.
- `data/raw/cost/`: public-price source URL, price date, assumptions and calculation CSV.
- `analysis/`: scripts that transform raw data into figures and tables.

## Cost model template

Record price-source date and region before calculating. State every assumption: event volume, average message size, DynamoDB read/write units, CloudWatch metrics/log retention, Lambda GB-seconds and API Gateway requests.

| Metric | Formula |
|---|---|
| Monthly platform cost | API Gateway + Lambda + SQS + DynamoDB + CloudWatch + storage |
| Cost per tenant/month | Monthly platform cost / active tenants |
| Cost per 1,000 requests | Monthly platform cost / (monthly requests / 1,000) |
| 100x projection | Recalculate with 100x events, tenants and required concurrency |

Use current published prices on the date of calculation; do not reuse vendor or cloud price claims without a dated source.
