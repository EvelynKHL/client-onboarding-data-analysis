# Client Onboarding Operations Analysis

A reproducible, portfolio-ready analysis of a **synthetic** client onboarding dataset. The project demonstrates data preparation, validation, KPI analysis, exception investigation, visualization, and business recommendations using Python's standard library.

> **Data notice:** Every record in `data/raw/onboarding_cases.csv` is fictional and generated for this project. It contains no real client, bank, or JPMorgan Chase data. The results are illustrative and should not be presented as actual company performance.

## Business question

Where do onboarding cases wait longest, what operational patterns are associated with late completion, and which data quality issues should an operations team address first?

## Key findings in this sample

The analysis script calculates these from the included data each time it runs. See [`reports/analysis_report.md`](reports/analysis_report.md) for the current results, assumptions, and recommendations.

## Project structure

```text
onboarding-data-analysis/
├── data/raw/onboarding_cases.csv      # Fictional input data
├── reports/analysis_report.md         # Generated findings and recommendations
├── reports/charts/                    # Generated SVG charts
├── scripts/generate_data.py           # Recreate the deterministic sample data
├── scripts/analyze.py                 # Validate, analyze, and write report outputs
└── requirements.txt                  # No third-party packages required
```

## Run the full process

Requires Python 3.9 or later. From this directory:

```bash
python scripts/generate_data.py
python scripts/analyze.py
```

The first command recreates the synthetic CSV with a fixed random seed. The second checks the input, calculates KPIs and breakdowns, then refreshes the Markdown report, summary CSVs, and SVG charts.

## Analysis process

1. **Load and validate:** check required columns, parse dates and numeric values, identify duplicate case IDs, missing fields, invalid categories, and impossible durations.
2. **Create analysis fields:** calculate processing days and an SLA flag (completed within 5 business days, excluding weekends). Cases still open at the snapshot date are reported separately.
3. **Measure outcomes:** summarize volume, completion, SLA attainment, processing time, and open backlog.
4. **Investigate patterns:** compare outcomes by onboarding channel, client segment, and exception category. Small groups are interpreted cautiously.
5. **Communicate actions:** generate charts and practical recommendations, with limitations stated in the report.

## Definitions and assumptions

- **Case:** one onboarding request, uniquely identified by `case_id`.
- **Snapshot date:** 2025-03-31. Open cases have no completion date; their elapsed age is measured to the snapshot date and is not treated as final processing time.
- **Business days:** Monday through Friday; public holidays are not modeled.
- **SLA:** five business days from received date through completion. It is an illustrative project assumption, not an actual JPMorgan Chase policy.
- **Data quality flags:** missing required fields, duplicate case IDs, unsupported category values, invalid dates, negative amounts, and completion before receipt.
- The generated sample intentionally includes a small number of data quality issues. Analysis excludes invalid date/duration records from processing-time calculations and reports the issues.
- Observed associations are descriptive, not causal. No personal or sensitive client information is present.

## Suggested GitHub description

Python portfolio project analyzing synthetic client onboarding operations, SLA performance, backlog, exceptions, and data quality with reproducible reports and charts.
