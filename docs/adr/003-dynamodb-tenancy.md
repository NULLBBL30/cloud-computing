# ADR 003 Tablestore tenancy

Decision: use one shared Tablestore table with `PK = TENANT#{tenant_id}` and `SK = PRODUCT#{product_id}`. Rejected alternatives: separate tables per tenant and a relational database. The design is low-operations and scalable; application code derives tenant identity from the API key and always scopes reads and writes by that key.
