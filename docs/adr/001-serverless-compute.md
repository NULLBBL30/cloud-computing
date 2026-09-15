# ADR 001 Serverless compute

Decision: use AWS Lambda behind API Gateway and for SQS processing. Rejected alternatives: ECS containers and self-managed virtual machines. Lambda reduces operational work and scales automatically; the trade-off is cold-start latency and provider coupling.
