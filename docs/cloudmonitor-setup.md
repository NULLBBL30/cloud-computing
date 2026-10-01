# CloudMonitor 5xx alarm setup

The deployment API credential can deploy Function Compute and Tablestore but the CloudMonitor `PutResourceMetricRule` call rejected the rule definition. Create the alert in the CloudMonitor console, where the account's active contact group can be selected explicitly.

1. Open CloudMonitor and create a metric alarm for the Function Compute service.
2. Select namespace `acs_fc`, function `inventory-platform/inventory-api`, and metric `FunctionHTTPStatus5xx`.
3. Set the period to 60 seconds and trigger a Critical alarm when the Average is greater than or equal to 1 for one consecutive period.
4. Select a contact group with at least one active contact, save the rule, and retain a screenshot showing the rule and its contact group.
5. Test with one malformed JSON request to the public `/events` endpoint. Confirm a 5xx metric and alarm history entry, then keep the invalid request out of all load-test data.

Function Compute uses the `acs_fc` namespace; its 5xx metric is `FunctionHTTPStatus5xx`, and metrics are aggregated at 60-second granularity. Function-level dimensions for FC 2.0 use the service and `{serviceName}${functionName}` values. See [Alibaba Cloud Function Compute monitoring data](https://help.aliyun.com/en/functioncompute/monitoring-data).

The malformed-request check validates HTTP 5xx alerting. It does not simulate a Tablestore outage. Keep the dependency failure experiment in `failure/tablestore_failure_test.md` separate and use an isolated test version if that experiment is performed.
