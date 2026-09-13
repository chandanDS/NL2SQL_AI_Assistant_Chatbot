# Increment 9 testing and release gate

## Automated gate

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest --cov=backend --cov-report=term-missing --cov-report=xml:outputs\coverage.xml -q
```

Current local baseline (2026-09-13):

- 259 tests passed
- 90% backend statement coverage
- 200-question golden dataset passed offline routing evaluation
- Formula, intent, RBAC, JWT, SQL injection, prompt injection, API integration, and E2E flows covered

Warnings currently come from upstream Starlette/FastAPI deprecations and do not fail the gate.

## Golden dataset

`tests/golden/banking_questions.jsonl` contains 200 version-controlled cases across:

- approved deterministic KPI questions
- governed dynamic semantic questions
- bank-wide RBAC denial wording
- ambiguous questions requiring LLM clarification

Regenerate deterministically with:

```powershell
.\.venv\Scripts\python.exe scripts\generate_golden_dataset.py
```

The default golden test is offline and consumes no OpenAI tokens. Dynamic cases verify routing boundaries;
run a separately budgeted sampled online evaluation before a production release to measure live model accuracy.

## Local Locust baseline

See `load_tests/README.md`. The 5-user, 20-second local smoke test produced:

- 72 requests
- 0 failures
- 24 ms aggregate median
- 320 ms aggregate maximum
- 23 ms median for `/analytics/query`
- 24 ms median for zero-token `/intent/interpret`

CSV evidence is under `outputs/locust_smoke_*.csv`.

This is a laptop smoke baseline, not a GCP capacity claim. Run the same workload against the GCP service,
then increase users gradually while enforcing agreed p95 latency, error-rate, database-pool, and API-quota thresholds.
