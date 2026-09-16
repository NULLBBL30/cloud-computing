# ADR 002 Synchronous event processing

Decision: process inventory events synchronously in the Function Compute HTTP handler and write them directly to Tablestore. We considered an MNS queued architecture, but rejected it for the initial platform because the expected coursework workload does not justify its additional operational cost and complexity. The trade-off is that request latency includes the database write, while the platform gains immediate read-after-write behaviour and avoids queue charges.
