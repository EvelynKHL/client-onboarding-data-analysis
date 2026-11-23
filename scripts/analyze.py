"""Validate and analyze synthetic onboarding cases; write reproducible outputs."""

import csv
import html
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "onboarding_cases.csv"
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
SNAPSHOT = date(2025, 3, 31)
SLA_BUSINESS_DAYS = 5
REQUIRED = {"case_id", "received_date", "completed_date", "client_segment",
            "onboarding_channel", "exception_category", "documents_complete",
            "risk_tier", "estimated_relationship_value_usd"}
ALLOWED = {
    "client_segment": {"Small Business", "Mid-Market", "Corporate"},
    "onboarding_channel": {"Digital", "Relationship Manager", "Branch"},
    "exception_category": {"None", "Missing Documentation", "Data Mismatch", "Risk Review"},
    "documents_complete": {"Y", "N"},
    "risk_tier": {"Low", "Medium", "High"},
}


def business_days(start: date, end: date) -> int:
    """Count weekdays after start through end; returns zero when end <= start."""
    if end <= start:
        return 0
    return sum(1 for ordinal in range(start.toordinal() + 1, end.toordinal() + 1)
               if date.fromordinal(ordinal).weekday() < 5)


def read_rows():
    with INPUT.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input is missing required columns: {sorted(missing)}")
        return list(reader)


def validate(rows):
    issues = Counter()
    seen = Counter(row["case_id"].strip() for row in rows)
    for row in rows:
        for field in REQUIRED - {"completed_date"}:
            if not row.get(field, "").strip():
                issues[f"Missing {field}"] += 1
        for field, allowed in ALLOWED.items():
            if row.get(field, "").strip() and row[field].strip() not in allowed:
                issues[f"Invalid {field}"] += 1
        if seen[row["case_id"].strip()] > 1:
            # Count duplicate rows after the first occurrence below instead.
            pass
        try:
            received = date.fromisoformat(row["received_date"])
            if received > SNAPSHOT:
                issues["Received date after snapshot"] += 1
            if row["completed_date"].strip():
                completed = date.fromisoformat(row["completed_date"])
                if completed < received:
                    issues["Completion before receipt"] += 1
                if completed > SNAPSHOT:
                    issues["Completion after snapshot"] += 1
        except (ValueError, TypeError):
            issues["Invalid date"] += 1
        try:
            if float(row["estimated_relationship_value_usd"]) < 0:
                issues["Negative relationship value"] += 1
        except (ValueError, TypeError):
            issues["Invalid relationship value"] += 1
    issues["Duplicate case ID rows"] = sum(count - 1 for count in seen.values() if count > 1)
    return issues


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def group_summary(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row[key]].append(row)
    result = []
    for label, items in sorted(groups.items()):
        done = [r for r in items if r["completed_date"]]
        within = [r for r in done if r["sla_days"] <= SLA_BUSINESS_DAYS]
        durations = [r["sla_days"] for r in done]
        result.append({
            "group": label, "cases": len(items), "completed": len(done),
            "open": len(items) - len(done),
            "sla_attainment_pct": round(100 * len(within) / len(done), 1) if done else "",
            "median_processing_business_days": round(statistics.median(durations), 1) if durations else "",
        })
    return result


def svg_bar(path, title, labels, values, color="#2463a6", suffix="%"):
    width, height = 820, 420
    left, right, top, bottom = 210, 35, 58, 55
    plot_w, plot_h = width - left - right, height - top - bottom
    maximum = max(values or [1])
    rows = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            f'<text x="{left}" y="30" font-family="Arial" font-size="20" font-weight="bold" fill="#172b4d">{html.escape(title)}</text>']
    n = max(len(labels), 1)
    slot = plot_h / n
    for i, (label, val) in enumerate(zip(labels, values)):
        y = top + i * slot + slot * 0.18
        bh = slot * 0.58
        bw = max(0, plot_w * val / maximum)
        rows.append(f'<text x="{left-12}" y="{y+bh*0.72:.1f}" text-anchor="end" font-family="Arial" font-size="14" fill="#344563">{html.escape(label)}</text>')
        rows.append(f'<rect x="{left}" y="{y:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{color}"/>')
        rows.append(f'<text x="{left+bw+8:.1f}" y="{y+bh*0.72:.1f}" font-family="Arial" font-size="14" fill="#172b4d">{val}{suffix}</text>')
    rows.append(f'<text x="{left}" y="{height-14}" font-family="Arial" font-size="12" fill="#6b778c">Illustrative synthetic data | Snapshot 2025-03-31</text>')
    rows.append('</svg>')
    path.write_text("\n".join(rows), encoding="utf-8")


def main():
    if not INPUT.exists():
        raise FileNotFoundError(f"Input not found: {INPUT}. Run scripts/generate_data.py first.")
    REPORTS.mkdir(parents=True, exist_ok=True)
    CHARTS.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    issues = validate(rows)
    valid_rows = []
    for row in rows:
        try:
            received = date.fromisoformat(row["received_date"])
            end = date.fromisoformat(row["completed_date"]) if row["completed_date"] else None
        except ValueError:
            continue
        if end and end < received:
            continue
        row["sla_days"] = business_days(received, end) if end else ""
        row["age_business_days"] = business_days(received, SNAPSHOT) if not end else ""
        valid_rows.append(row)
    completed = [r for r in valid_rows if r["completed_date"]]
    open_rows = [r for r in valid_rows if not r["completed_date"]]
    durations = [r["sla_days"] for r in completed]
    on_time = sum(r["sla_days"] <= SLA_BUSINESS_DAYS for r in completed)
    overall = {
        "total_cases": len(rows), "valid_date_cases": len(valid_rows),
        "completed_cases": len(completed), "open_cases": len(open_rows),
        "completion_rate_pct": round(100 * len(completed) / len(valid_rows), 1) if valid_rows else 0,
        "sla_attainment_pct": round(100 * on_time / len(completed), 1) if completed else 0,
        "median_processing_business_days": round(statistics.median(durations), 1) if durations else 0,
        "average_processing_business_days": round(statistics.mean(durations), 1) if durations else 0,
        "open_over_5_business_days": sum(int(r["age_business_days"]) > 5 for r in open_rows),
    }
    write_csv(REPORTS / "overall_kpis.csv", [overall], list(overall))
    group_outputs = {}
    for key, filename in [("onboarding_channel", "by_channel.csv"), ("client_segment", "by_segment.csv"),
                          ("exception_category", "by_exception.csv")]:
        summary = group_summary(valid_rows, key)
        write_csv(REPORTS / filename, summary, list(summary[0]) if summary else ["group"])
        group_outputs[key] = summary
    issue_rows = [{"issue": name, "count": count} for name, count in sorted(issues.items()) if count]
    write_csv(REPORTS / "data_quality_issues.csv", issue_rows, ["issue", "count"])

    channels = [r for r in group_outputs["onboarding_channel"] if r["sla_attainment_pct"] != ""]
    exceptions = [r for r in group_outputs["exception_category"] if r["median_processing_business_days"] != ""]
    svg_bar(CHARTS / "sla_by_channel.svg", "Completed within 5 business days by channel",
            [r["group"] for r in channels], [r["sla_attainment_pct"] for r in channels])
    svg_bar(CHARTS / "median_days_by_exception.svg", "Median processing time by exception category",
            [r["group"] for r in exceptions], [r["median_processing_business_days"] for r in exceptions], color="#8b5fbf", suffix=" days")
    svg_bar(CHARTS / "data_quality_issues.svg", "Detected data quality issues",
            [r["issue"] for r in issue_rows], [r["count"] for r in issue_rows], color="#d97706", suffix=" rows")

    slowest_days = max((float(r["median_processing_business_days"]) for r in exceptions), default=None)
    slowest = [r["group"] for r in exceptions if float(r["median_processing_business_days"]) == slowest_days] if slowest_days is not None else []
    best_channel = max(channels, key=lambda r: float(r["sla_attainment_pct"])) if channels else None
    report = f'''# Client Onboarding Operations Analysis

**Dataset:** fictional, deterministically generated sample | **Snapshot:** 2025-03-31  
**Purpose:** demonstrate an end-to-end operational data analysis workflow. These findings do not describe any real bank or its clients.

## Executive summary

- **{overall['total_cases']:,}** cases were included; **{overall['completed_cases']:,}** were completed and **{overall['open_cases']:,}** remained open at the snapshot.
- Completion rate among date-valid cases: **{overall['completion_rate_pct']}%**. SLA attainment among completed cases: **{overall['sla_attainment_pct']}%** within the illustrative five-business-day target.
- Completed cases had a median processing time of **{overall['median_processing_business_days']} business days** (mean: {overall['average_processing_business_days']} days).
- **{overall['open_over_5_business_days']:,}** open cases were older than five business days at the snapshot.
- Validation found **{sum(issues.values()):,} issue occurrences** across {len([x for x in issues.values() if x])} issue types. A row may contribute to more than one issue type.

## KPI definitions

| KPI | Result | Definition |
|---|---:|---|
| Total cases | {overall['total_cases']:,} | Input rows, including rows flagged by quality checks |
| Completion rate | {overall['completion_rate_pct']}% | Completed / date-valid cases |
| SLA attainment | {overall['sla_attainment_pct']}% | Completed in 5 or fewer business days / completed cases |
| Median processing time | {overall['median_processing_business_days']} days | Median weekday count between receipt and completion |
| Open backlog over 5 days | {overall['open_over_5_business_days']:,} | Still-open cases older than 5 business days on snapshot date |

## Findings

### Channel comparison

![SLA attainment by channel](charts/sla_by_channel.svg)

'''
    for r in channels:
        report += f"- **{r['group']}:** {r['sla_attainment_pct']}% within SLA across {r['completed']} completed cases (median {r['median_processing_business_days']} business days).\n"
    if best_channel:
        report += f"\nThe highest observed channel SLA attainment was **{best_channel['group']}**. This is a descriptive result from randomized fictional data and is not evidence that the channel caused the difference.\n"
    report += '''
### Exception comparison

![Processing time by exception category](charts/median_days_by_exception.svg)

'''
    for r in exceptions:
        report += f"- **{r['group']}:** median {r['median_processing_business_days']} business days across {r['completed']} completed cases; SLA attainment {r['sla_attainment_pct']}%.\n"
    if slowest:
        report += f"\n**{', '.join(slowest)}** had the longest median processing time in this sample. Use this as a prompt to inspect handoffs and case notes, not as a causal conclusion.\n"
    report += '''
### Data quality

![Data quality issue counts](charts/data_quality_issues.svg)

| Issue type | Rows |
|---|---:|
'''
    if issue_rows:
        for r in issue_rows:
            report += f"| {r['issue']} | {r['count']} |\n"
    else:
        report += "| No issues detected | 0 |\n"
    report += '''
## Recommended operational actions

1. **Triage aged open cases daily.** Start with cases beyond the five-day illustrative target; assign an owner, next action, and due date.
2. **Prevent avoidable document exceptions.** Use a standardized intake checklist and clear missing-document requests, then track repeat causes.
3. **Add validation at intake.** Require key fields, enforce permitted values, and check date and amount plausibility before a case enters downstream processing.
4. **Review exception handoffs.** Map the steps for risk review and data mismatch cases; measure time waiting at each handoff before changing the process.
5. **Monitor trends with richer data.** In a real analysis, segment by complexity, staffing, product, geography, holiday calendar, and case age while applying privacy and access controls.

## Limitations

- Synthetic data is generated for demonstration; counts, distributions, and relationships have no real-world evidentiary value.
- Cases are randomly assigned channel, segment, exception, and risk tier. Differences across groups are illustrative and not causal.
- The five-business-day target is a project assumption, and the weekday calendar excludes holidays.
- The data has no timestamps for intermediate steps, so it cannot isolate queue time from active processing time.
- Relationship value is included only for schema practice and is not used to rank clients or make decisions.

## Reproducibility

Run `python scripts/generate_data.py` followed by `python scripts/analyze.py`. Tabular outputs are in this folder: `overall_kpis.csv`, `by_channel.csv`, `by_segment.csv`, `by_exception.csv`, and `data_quality_issues.csv`.
'''
    (REPORTS / "analysis_report.md").write_text(report, encoding="utf-8")
    print(f"Analyzed {len(rows)} rows; report and outputs written to {REPORTS}")


if __name__ == "__main__":
    main()
