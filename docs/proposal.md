# A Cloud-Based Multi-Tenant Inventory Event Platform for Electronics Retail

## Industry, customer and problem

This project addresses electronics retail, using Power City Ireland as a named customer scenario for a multi-location retailer. The project does not make claims about Power City's current systems. Instead, it investigates how a reusable platform could process inventory events for retailers with shops and warehouses, while also serving other retailers as isolated tenants.

Retail locations continuously generate sale, return, stock-received and adjustment events. Demand is variable: normal trading creates a modest flow, whereas promotions, product launches and holiday periods can produce sharp bursts. A system permanently sized for peak traffic wastes capacity; one sized for average traffic risks delayed updates under bursts. A shared platform also has a strict requirement that one retailer must never read or modify another retailer's inventory.

## Platform concept

Store clients submit inventory events to an Alibaba Cloud Function Compute HTTP endpoint. The API derives the tenant from an API credential rather than trusting a tenant identifier supplied by the client. It synchronously suppresses duplicate event identifiers and updates tenant-partitioned inventory state in Tablestore. Function Compute logs and metrics expose request volume, errors and latency.

The prototype intentionally excludes a storefront, payments, purchasing workflows and ERP functions. Its contribution is a narrow, measurable inventory-event platform with an explicit multi-tenant boundary.

## Why cloud?

The principal cloud driver is elasticity. Event demand can vary significantly between routine trading and promotion periods. Function Compute scales the HTTP handler without manual server provisioning, while Tablestore provides a managed data store. The initial workload does not justify the operating cost and complexity of a dedicated message queue, so the prototype deliberately uses synchronous processing and measures user-visible latency under load.

Multi-tenancy is the supporting driver: one codebase and shared services can support multiple retailers while preserving logical separation through tenant-derived partition keys and authorization checks. This provides an economical platform model that a single-machine, single-customer application does not address.

## Initial success criteria

The platform targets p50/p95/p99 event-submission latency below 100/250/500 ms at 50 RPS across ten tenants; zero successful cross-tenant reads or writes; and 99.9% design availability. Evaluation will include at least five load levels up to degradation, direct-write failure handling, measured scaling delay, and published-price cost modelling per tenant and per 1,000 requests. The deployed platform will be reachable during the assessment window.
