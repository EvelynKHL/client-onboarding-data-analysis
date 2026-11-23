"""Generate deterministic fictional onboarding cases for the portfolio project."""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "onboarding_cases.csv"
SNAPSHOT = date(2025, 3, 31)


def add_business_days(start: date, days: int) -> date:
    current = start
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def main() -> None:
    rng = random.Random(210706687)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    start = date(2025, 1, 1)
    weekdays = [start + timedelta(days=i) for i in range((SNAPSHOT - start).days + 1)
                if (start + timedelta(days=i)).weekday() < 5]
    for i in range(1, 601):
        received = rng.choice(weekdays)
        segment = rng.choices(["Small Business", "Mid-Market", "Corporate"], [42, 36, 22])[0]
        channel = rng.choices(["Digital", "Relationship Manager", "Branch"], [48, 34, 18])[0]
        exception = rng.choices(["None", "Missing Documentation", "Data Mismatch", "Risk Review"],
                                [56, 19, 15, 10])[0]
        # Exception and channel influence the fictional processing-time distribution.
        base = {"Digital": 2, "Relationship Manager": 3, "Branch": 3}[channel]
        delay = {"None": 0, "Missing Documentation": 4,
                 "Data Mismatch": 3, "Risk Review": 5}[exception]
        duration = max(1, int(rng.triangular(1, 12, base + delay)))
        completion_date = add_business_days(received, duration)
        # A case cannot be completed beyond the declared reporting snapshot.
        is_open = completion_date > SNAPSHOT or rng.random() < 0.035
        completed = "" if is_open else completion_date.isoformat()
        # A few intentionally imperfect records support the validation exercise.
        missing_docs = "Y" if exception == "Missing Documentation" else "N"
        if i in (17, 204):
            missing_docs = ""
        amount = round(rng.uniform(5000, 2500000), 2)
        if i == 311:
            amount = -500.0
        risk = rng.choices(["Low", "Medium", "High"], [48, 37, 15])[0]
        rows.append({
            "case_id": f"ONB-{i:04d}",
            "received_date": received.isoformat(),
            "completed_date": completed,
            "client_segment": segment,
            "onboarding_channel": channel,
            "exception_category": exception,
            "documents_complete": missing_docs,
            "risk_tier": risk,
            "estimated_relationship_value_usd": f"{amount:.2f}",
        })
    # A duplicate ID is deliberate; downstream validation will flag it.
    rows[-1]["case_id"] = rows[10]["case_id"]
    fields = list(rows[0])
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} fictional cases to {OUT}")


if __name__ == "__main__":
    main()
