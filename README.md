# Serverless Multi Tenant Inventory Platform on Alibaba Cloud

The assessed system is a course prototype for multi-store retailers. A public Alibaba Cloud Function Compute HTTP trigger authenticates a tenant from an API key, validates an inventory event, and conditionally appends one event row to a tenant-partitioned Tablestore table. Inventory reads derive quantity from the legacy opening balance plus the matching event deltas. The browser console is a demonstration client, not the platform boundary.

## Deployment

GitHub Actions reads `ALICLOUD_ACCESS_KEY`, `ALICLOUD_SECRET_KEY`, `TENANT_KEYS_JSON` and `TF_STATE_BUCKET` from repository Secrets, builds the FC package, runs tests and applies Terraform. Terraform stores remote state in OSS. No credential is committed to this repository. The default region is `cn-hangzhou`.

Push the repository's `main` branch, then inspect the Actions run and retrieve the HTTP Trigger URL from Function Compute. Keep the endpoint reachable for the assessment window.

## Functional demonstration

Open the Function Compute public HTTPS endpoint in a browser. The bundled page supports a live demonstration using `demo-key-a` and `demo-key-b`:

1. Submit a `STOCK_RECEIVED` event using a new `event_id` for tenant A.
2. Query the same product as tenant A and record the updated quantity.
3. Submit the same `event_id` again and confirm `duplicate ignored` with no quantity change.
4. Switch to tenant B and confirm that the tenant A product cannot be read.

Run `python -m pytest -q` to verify the same isolation, idempotency, API-key rejection and CORS behaviour without cloud credentials.

## Evaluation

Run `./scripts/run-evaluation.ps1 -BaseUrl <fc-http-trigger-url>` and retain raw results in `data/raw/`. Use the five-level load, scaling and fault protocol in `docs/evaluation-plan.md` against the deployed endpoint.

### Inventory write model

Each accepted event is one conditional Tablestore row write keyed by tenant and `event_id`. Concurrent duplicate submissions therefore have one winner, while distinct events cannot overwrite one another's quantity updates. A retry after an uncertain write response sees the existing event and does not apply the change twice. No cross-row transaction is used.

Inventory reads sum the matching event deltas and add the existing `PRODUCT#...` row as an opening-balance snapshot. This preserves quantities already stored before the event-ledger deployment; older event rows without a delta are ignored because their effects are already reflected in that snapshot. The tradeoff is that reads scan the tenant's event rows and become more expensive as history grows. Record this limitation when reporting load and cost results.

## Submission documents

- `docs/proposal.md`
- `docs/requirements.md`
- `docs/adr/`
- `docs/evaluation-plan.md`
- `docs/quick-evaluation-results.md`
- `docs/paper-outline.md`
- `docs/presentation-plan.md`
- `docs/operations-runbook.md`
- `docs/evidence-register.md`
