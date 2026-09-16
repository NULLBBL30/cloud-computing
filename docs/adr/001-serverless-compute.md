# ADR 001 Serverless compute

Decision: use Alibaba Cloud Function Compute behind an HTTP trigger. Rejected alternatives: containers and self-managed virtual machines. Function Compute reduces operational work and scales automatically; the trade-off is cold-start latency and provider coupling.
