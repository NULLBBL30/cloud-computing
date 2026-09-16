# ADR 006 Identity and secrets

Decision: map API keys to tenants in Function Compute environment configuration, injected by GitHub Actions secrets and Terraform variables. Rejected alternative: tenant identifiers in request payloads. The design prevents client-selected tenancy; API keys need rotation and should later be replaced by a managed identity provider. The public browser console exposes only course-demo keys, never cloud credentials.
