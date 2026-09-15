# A Cloud-Based Multi-Tenant Inventory Event Platform for Electronics Retail

## Industry, customer and problem

This project addresses electronics retail, using Power City Ireland as a named customer scenario for a multi-location retailer. The project does not make claims about Power City's current systems. Instead, it investigates how a reusable platform could process inventory events for retailers with shops and warehouses, while also serving other retailers as isolated tenants.

Retail locations continuously generate sale, return, stock-received and adjustment events. Demand is variable: normal trading creates a modest flow, whereas promotions, product launches and holiday periods can produce sharp bursts. A system permanently sized for peak traffic wastes capacity; one sized for average traffic risks delayed updates under bursts. A shared platform also has a strict requirement that one retailer must never read or modify another retailer's inventory.

## Platform concept

Store clients submit inventory events to an AWS API Gateway endpoint backed by FastAPI on AWS Lambda. The API derives the tenant from an API credential, rather than trusting a tenant identifier supplied by the client. It acknowledges the event and places it on Amazon SQS. An SQS-triggered Lambda worker processes the event, suppresses duplicate event identifiers, and updates tenant-partitioned inventory state in Amazon DynamoDB. CloudWatch metrics, logs and a queue-backlog alarm expose accepted events, processed events and queue backlog.

The prototype intentionally excludes a storefront, payments, purchasing workflows and ERP functions. Its contribution is a narrow, measurable inventory-event platform with an explicit multi-tenant boundary.

## Why cloud?

The principal cloud driver is elasticity. Event demand can vary significantly between routine trading and promotion periods. Queue-based asynchronous processing separates client responsiveness from back-end processing capacity. API Gateway, Lambda and the SQS-to-Lambda event source mapping scale without manual intervention. The project will measure the delay from a load spike to increased Lambda concurrency and the resulting user-visible latency.

Multi-tenancy is the supporting driver: one codebase and shared services can support multiple retailers while preserving logical separation through tenant-derived partition keys and authorization checks. This provides an economical platform model that a single-machine, single-customer application does not address.

## Initial success criteria

The platform targets p50/p95/p99 event-submission latency below 100/250/500 ms at 50 RPS across ten tenants; zero successful cross-tenant reads or writes; and 99.9% design availability. Evaluation will include at least five load levels up to degradation, a worker-failure recovery experiment, measured scaling delay, and published-price cost modelling per tenant and per 1,000 requests. The deployed platform will be reachable during the assessment window.
