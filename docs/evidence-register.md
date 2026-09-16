# Evidence register

| ID | Requirement demonstrated | Evidence to retain | Status |
|---|---|---|---|
| E1 | Public deployed platform | Function Compute public endpoint and browser console screenshot | Complete |
| E2 | Tenant isolation | Tenant A reads stock and tenant B receives not found for the same SKU | Pending capture |
| E3 | Idempotency | Repeated event ID returns `duplicate ignored` and quantity remains unchanged | Pending capture |
| E4 | Infrastructure as Code | Terraform `main.tf` and successful GitHub Actions deployment | Complete |
| E5 | CI/CD | Latest green Actions run showing test, package and Terraform apply | Complete |
| E6 | Managed persistence | Tablestore instance/table console screenshot | Pending capture |
| E7 | Observability | FC log, CloudMonitor metric and alarm screenshots | Pending capture |
| E8 | Five load levels | Locust raw CSV files and generated `data/derived/load-summary.csv` | Pending execution |
| E9 | Scaling | Timestamped Function Compute monitoring screenshots and spike timeline | Pending execution |
| E10 | Failure and recovery | Controlled test-version failure, alert and recovery evidence | Pending execution |
| E11 | Cost | Alibaba Cloud bill by product and stated modelling assumptions | Pending capture |
