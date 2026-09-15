# Worker-failure experiment

1. Start the platform with `./scripts/deploy.ps1 -KeepRunning`.
2. Start Locust at 50 requests/s and save its CSV output under `data/raw/failure/`.
3. Record the worker process ID, then stop only that worker process for 60 seconds.
4. Record API error rate, SQS visible-message count, stop time, restart time, and queue-drain completion time.
5. Restart `python -m worker.worker`; retain every CSV and log file.

Expected result: API event submission remains `202 Accepted`, queue depth rises during the outage, then drains after restart. Inventory reads are eventually consistent during the outage.
