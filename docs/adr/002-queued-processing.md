# ADR 002 Queued processing

Decision: accept events asynchronously through SQS. Rejected alternative: synchronous API-to-database updates. SQS absorbs bursts and isolates worker failure; the trade-off is eventual consistency and duplicate delivery.
