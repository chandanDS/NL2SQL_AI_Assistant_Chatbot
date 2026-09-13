import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tests" / "golden" / "banking_questions.jsonl"
MONTHS = ["January", "February", "March", "April", "May", "June", "August", "September"]
FIXED = [
    ("DEPOSITS", "DEPOSIT_BUSINESS_AMOUNT", "Show total savings deposit amount for {month} 2026", ["SA"]),
    ("DEPOSITS", "DEPOSIT_ACCOUNT_COUNT", "Show number of CASA accounts for {month} 2026", ["CA", "SA"]),
    ("DEPOSITS", "DEPOSIT_NEW_ACCOUNTS", "Show new current accounts opened in {month} 2026", ["CA"]),
    ("ADVANCES", "ADVANCE_OUTSTANDING_AMOUNT", "Show home loan outstanding amount for {month} 2026", ["HL"]),
    ("ADVANCES", "ADVANCE_ACCOUNT_COUNT", "Show number of MSME loan accounts for {month} 2026", ["MSME"]),
    ("ADVANCES", "ADVANCE_DISBURSEMENT_AMOUNT", "Show vehicle loan disbursement for {month} 2026", ["VL"]),
    ("NPA_SMA", "ASSET_QUALITY_OUTSTANDING_AMOUNT", "Show SMA2 outstanding amount for {month} 2026", ["SMA2"]),
    ("NPA_SMA", "ASSET_QUALITY_ACCOUNT_COUNT", "Show number of doubtful accounts for {month} 2026", ["DOUBTFUL"]),
    ("NPA_SMA", "ASSET_QUALITY_RECOVERY_AMOUNT", "Show NPA recovery for {month} 2026", []),
    ("DIGITAL", "DIGITAL_REGISTERED_CUSTOMERS", "Show registered UPI customers for {month} 2026", ["UPI"]),
    ("DIGITAL", "DIGITAL_ACTIVE_CUSTOMERS", "Show active mobile banking customers for {month} 2026", ["MOBILE_BANKING"]),
    ("DIGITAL", "DIGITAL_TRANSACTION_COUNT", "Show UPI transaction count for {month} 2026", ["UPI"]),
    ("DIGITAL", "DIGITAL_TRANSACTION_AMOUNT", "Show debit card transaction amount for {month} 2026", ["DEBIT_CARD"]),
]
DYNAMIC = [
    ("ADVANCES", "Show average home loan ticket size for {month} 2026"),
    ("ADVANCES", "Show overdue amount as percentage of advances for {month} 2026"),
    ("DEPOSITS", "Show average savings balance per account for {month} 2026"),
    ("DEPOSITS", "Rank branches by current account balance for {month} 2026"),
    ("NPA_SMA", "Show recovery to slippage ratio for {month} 2026"),
    ("NPA_SMA", "Show average NPA outstanding per account for {month} 2026"),
    ("DIGITAL", "Show active customer percentage by product for {month} 2026"),
    ("DIGITAL", "Show transaction amount per active customer for {month} 2026"),
]


def main():
    rows = []
    for module, kpi, template, products in FIXED:
        for month in MONTHS:
            rows.append({"question": template.format(month=month), "expected_route": "deterministic",
                         "module": module, "kpi": kpi, "products": products})
    for module, template in DYNAMIC:
        for month in MONTHS:
            rows.append({"question": template.format(month=month), "expected_route": "dynamic",
                         "module": module, "kpi": None, "products": []})
    for index in range(16):
        phrase = ("bank as a whole", "entire bank", "bank-wide", "across the bank")[index % 4]
        rows.append({"question": f"Show deposits for {phrase} in September 2026", "expected_route": "rbac_denied",
                     "module": "DEPOSITS", "kpi": "DEPOSIT_BUSINESS_AMOUNT", "products": []})
    for index in range(16):
        rows.append({"question": f"Tell me the banking result for case {index + 1}", "expected_route": "clarification",
                     "module": None, "kpi": None, "products": []})
    assert len(rows) == 200
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(rows, 1):
            handle.write(json.dumps({"id": f"BQ-{index:03d}", **row}) + "\n")
    print(f"Wrote {len(rows)} questions to {OUTPUT}")


if __name__ == "__main__":
    main()
