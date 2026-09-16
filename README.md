# Multi Tenant Inventory Event Platform

The assessed deployment uses an Alibaba Cloud Function Compute HTTP Trigger and Tablestore. Inventory events are synchronously applied with idempotency protection; local moto is retained only for fast unit tests.

## Deployment

GitHub Actions reads `ALICLOUD_ACCESS_KEY`, `ALICLOUD_SECRET_KEY` and `TENANT_KEYS_JSON` from repository Secrets, builds the FC package, runs tests and applies Terraform. No credential is committed to this repository. The default region is `cn-hangzhou`.

Push the repository's `main` branch, then inspect the Actions run and retrieve the HTTP Trigger URL from Function Compute. Keep the endpoint reachable for the assessment window.

## Local validation

Run `./scripts/deploy.ps1 -KeepRunning` for local moto tests only, or `python -m pytest -q` to verify tenant isolation and event idempotency.

## Evaluation

Run `locust -f load/locustfile.py --host <fc-http-trigger-url>` and retain raw results in `data/raw/`. Use the five-level load, scaling and fault protocol in `docs/evaluation-plan.md` against the deployed endpoint rather than moto.

## Submission documents

- `docs/proposal.md`
- `docs/requirements.md`
- `docs/adr/`
- `docs/evaluation-plan.md`
- `docs/paper-outline.md`
- `docs/presentation-plan.md`
