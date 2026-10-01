# Evidence register

| ID | Requirement demonstrated | Evidence to retain | Status |
|---|---|---|---|
| E1 | Public deployed platform | Function Compute public endpoint and browser console screenshot | Complete |
| E2 | Tenant isolation | Tenant A reads stock and tenant B receives not found for the same SKU | Captured in `data/raw/functional-smoke/20261001/api-smoke.json` |
| E3 | Event-ledger integrity | New events change derived quantity; replayed event IDs are ignored; concurrent distinct events all contribute | New event and replay captured in `data/raw/functional-smoke/20261001/api-smoke.json`; concurrent distinct events pending |
| E4 | Infrastructure as Code | Terraform `main.tf` and successful GitHub Actions deployment | Complete |
| E5 | CI/CD | Latest green Actions run showing test, package and Terraform apply | Complete |
| E6 | Managed persistence | Tablestore instance/table console screenshot | Pending capture |
| E7 | Observability | FC log, CloudMonitor metric and alarm screenshots | Pending: create the 5xx alarm in the console and select an enabled contact group; see `docs/cloudmonitor-setup.md` |
| E8 | Five load levels | Short live baseline CSV files and `docs/quick-evaluation-results.md`; repeat three full runs before final submission | Baseline complete |
| E9 | Scaling | Timestamped Function Compute monitoring screenshots and spike timeline | Pending execution |
| E10 | Failure and recovery | Controlled test-version failure, alert and recovery evidence | Pending execution |
| E11 | Cost | Alibaba Cloud bill by product and stated modelling assumptions | Pending capture |
