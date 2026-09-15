# ADR 003 DynamoDB tenancy

Decision: use a shared DynamoDB table with `TENANT#id` partition keys. Rejected alternatives: separate tables per tenant and a relational database. The design is low-operations and scalable; application code must enforce tenant scoping.
