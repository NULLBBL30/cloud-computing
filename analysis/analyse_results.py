"""Summarise Locust CSV files without changing raw data or requiring pandas."""
import csv
from pathlib import Path

columns = ["Name", "Request Count", "Failure Count", "Average Response Time", "95%", "99%"]
for path in Path("data/raw").rglob("*_stats.csv"):
    print(f"\n{path}")
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            print(" | ".join(f"{column}: {row.get(column, '-') }" for column in columns))
