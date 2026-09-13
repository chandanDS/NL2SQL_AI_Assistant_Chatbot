import os
import random

from locust import HttpUser, between, task


class BankingAnalyticsUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        password = os.environ.get("LOAD_TEST_PASSWORD")
        if not password:
            raise RuntimeError("Set LOAD_TEST_PASSWORD before starting Locust")
        response = self.client.post("/auth/login", data={
            "username": os.environ.get("LOAD_TEST_USERNAME", "bankuser0137"),
            "password": password,
        }, name="POST /auth/login")
        response.raise_for_status()
        self.headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(5)
    def approved_kpi(self):
        kpi, products = random.choice([
            ("DEPOSIT_BUSINESS_AMOUNT", ["SA"]),
            ("DEPOSIT_ACCOUNT_COUNT", ["CA", "SA"]),
            ("ADVANCE_OUTSTANDING_AMOUNT", ["HL"]),
            ("ASSET_QUALITY_RECOVERY_AMOUNT", ["SMA2"]),
            ("DIGITAL_TRANSACTION_COUNT", ["UPI"]),
        ])
        with self.client.post("/analytics/query", headers=self.headers, json={
            "kpi_code": kpi, "period_start": "2026-09-01", "period_end": "2026-09-01",
            "products": products, "comparison": "none",
        }, name="POST /analytics/query", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text[:160]}")

    @task(2)
    def zero_token_intent(self):
        with self.client.post("/intent/interpret", headers=self.headers, json={
            "message": "Show total savings deposit amount for September 2026"
        }, name="POST /intent/interpret [fast]", catch_response=True) as response:
            if response.status_code != 200 or response.json().get("usage", {}).get("total_tokens") != 0:
                response.failure("Fast intent path failed or unexpectedly used LLM tokens")
