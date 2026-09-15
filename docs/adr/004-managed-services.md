# ADR 004 Managed services

Decision: use API Gateway, Lambda, SQS, DynamoDB and CloudWatch rather than self-hosted equivalents. The reason is measured elasticity and reduced administration; the trade-off is AWS dependency and usage-based costs.
