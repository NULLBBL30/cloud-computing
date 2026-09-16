# Tablestore failure experiment

Use this controlled experiment only after functional evidence has been captured from the presentation deployment.

1. Run the `Target` load profile from `docs/evaluation-plan.md` and save its CSV files.
2. Create a temporary Function Compute test version whose `OTS_TABLE` environment value is `inventory-invalid-test`.
3. Route the test alias to that version for 60 seconds while the load test continues.
4. Preserve the load CSV, Function Compute invocation/error screenshots, SLS logs and alert screenshot.
5. Restore the correct `inventory` table value and measure time until successful writes resume.

Expected behaviour: API writes fail during the dependency outage, CloudMonitor reports errors, and the production alias remains unchanged. The report must state the measured error rate and recovery time rather than claiming resilience without evidence.
