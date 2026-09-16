"""Create a report-ready summary from raw Locust statistics without pandas."""
import csv
from pathlib import Path


RAW_ROOT = Path("data/raw/load")
OUTPUT = Path("data/derived/load-summary.csv")
FIELDS = ["profile", "endpoint", "requests", "failures", "error_rate_percent", "average_ms", "p50_ms", "p95_ms", "p99_ms"]


def number(row, name):
    return float((row.get(name) or "0").replace(",", ""))


def main():
    summaries = []
    for path in sorted(RAW_ROOT.rglob("locust_stats.csv")):
        profile = path.parent.name.rsplit("-", 1)[-1]
        with path.open(newline="", encoding="utf-8") as stream:
            rows = [row for row in csv.DictReader(stream) if row.get("Name") != "Aggregated"]
        for row in rows:
            requests = number(row, "Request Count")
            failures = number(row, "Failure Count")
            summaries.append({
                "profile": profile,
                "endpoint": row.get("Name", ""),
                "requests": int(requests),
                "failures": int(failures),
                "error_rate_percent": round(100 * failures / requests, 3) if requests else 0,
                "average_ms": row.get("Average Response Time", ""),
                "p50_ms": row.get("50%", ""),
                "p95_ms": row.get("95%", ""),
                "p99_ms": row.get("99%", ""),
            })
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(summaries)
    print(f"Wrote {len(summaries)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
