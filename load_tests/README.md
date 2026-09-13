# Local Locust load test

Set the password in the current PowerShell session; never put it in the locustfile:

```powershell
$env:LOAD_TEST_PASSWORD = '<synthetic-user-password>'
locust -f load_tests/locustfile.py --host http://127.0.0.1:8000
```

Bounded headless smoke test:

```powershell
locust -f load_tests/locustfile.py --host http://127.0.0.1:8000 --headless -u 5 -r 1 -t 20s --csv outputs/locust_smoke
```

This default workload avoids paid LLM calls. Run larger tests only after reviewing laptop CPU,
database pool limits, API quotas, expected concurrency, and acceptable latency/error thresholds.
