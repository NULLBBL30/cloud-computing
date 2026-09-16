# Operations runbook

## Demonstration baseline

Keep the Function Compute HTTP trigger public only for the assessment period. The application still requires `x-api-key` for inventory reads and writes. Use only the demo keys in the browser console. Keep Alibaba Cloud access keys only in GitHub repository secrets.

## Log evidence

In the Alibaba Cloud console, open Function Compute, select `inventory-platform` and `inventory-api`, then open the Logs tab. During a successful submission, retain a screenshot with the function name, timestamp and successful invocation. During the controlled dependency test, retain the matching error log screenshot.

## Metrics and alarm evidence

In CloudMonitor, create an alarm rule for the Function Compute function's invocation error metric. Configure a short evaluation window suitable for the experiment and an error threshold above zero. Capture the rule configuration before testing and its triggered state during the controlled dependency experiment. Delete or disable the alert after assessment if no longer needed.

## Scaling evidence

Before the 10-to-100 user jump, record the Function Compute monitoring view with timestamp. Record the first sustained concurrency or instance-count increase during the load spike, then record the return-to-baseline view. The report calculates scaling delay from the spike timestamp to that first sustained increase.

## Recovery evidence

Use only a temporary alias or test version for the invalid-Tablestore experiment in `failure/tablestore_failure_test.md`. Do not alter the production alias used for the live demonstration. Restore the correct configuration immediately after 60 seconds and record the first successful API write.

## Cost evidence

Record the Alibaba Cloud billing page by product after the tests. Save the date, region, Function Compute, Tablestore, OSS and log costs. The report must distinguish observed billed cost from projected monthly cost.
