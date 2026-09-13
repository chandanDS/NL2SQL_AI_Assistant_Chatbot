import json
from pathlib import Path

import pytest

from backend.llm.intent_service import try_fast_intent
from backend.rbac.scope import requests_bank_wide_scope


DATASET = Path(__file__).with_name("banking_questions.jsonl")
CASES = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines()]


def test_golden_dataset_size_and_unique_ids():
    assert 150 <= len(CASES) <= 300
    assert len({case["id"] for case in CASES}) == len(CASES)


@pytest.mark.golden
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_offline_golden_routing(case):
    route = case["expected_route"]
    if route == "deterministic":
        resolved = try_fast_intent(case["question"])
        assert resolved is not None
        intent, request = resolved
        assert intent.module.value == case["module"]
        assert request.kpi_code == case["kpi"]
        assert request.products == case["products"]
    elif route == "rbac_denied":
        assert requests_bank_wide_scope(case["question"])
    else:
        assert try_fast_intent(case["question"]) is None
