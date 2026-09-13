from dataclasses import dataclass
from typing import Any

from backend.models.banking import AdvanceMonthlyFact, AssetQualityMonthlyFact, DepositMonthlyFact, DigitalProductMonthlyFact


@dataclass(frozen=True)
class Measure:
    column: Any
    unit: str


@dataclass(frozen=True)
class SemanticDataset:
    model: type[Any]
    product_column: Any
    allowed_products: frozenset[str]
    measures: dict[str, Measure]


SEMANTIC_DATASETS = {
    "DEPOSITS": SemanticDataset(
        DepositMonthlyFact, DepositMonthlyFact.product_type, frozenset({"CA", "SA"}),
        {
            "business_amount": Measure(DepositMonthlyFact.business_amount, "INR"),
            "target_amount": Measure(DepositMonthlyFact.target_amount, "INR"),
            "account_count": Measure(DepositMonthlyFact.account_count, "ACCOUNTS"),
            "target_account_count": Measure(DepositMonthlyFact.target_account_count, "ACCOUNTS"),
            "new_accounts": Measure(DepositMonthlyFact.new_accounts, "ACCOUNTS"),
            "closed_accounts": Measure(DepositMonthlyFact.closed_accounts, "ACCOUNTS"),
        },
    ),
    "ADVANCES": SemanticDataset(
        AdvanceMonthlyFact, AdvanceMonthlyFact.product_type, frozenset({"EL", "VL", "PL", "HL", "MSME", "AGRI"}),
        {
            "outstanding_amount": Measure(AdvanceMonthlyFact.outstanding_amount, "INR"),
            "target_amount": Measure(AdvanceMonthlyFact.target_amount, "INR"),
            "account_count": Measure(AdvanceMonthlyFact.account_count, "ACCOUNTS"),
            "target_account_count": Measure(AdvanceMonthlyFact.target_account_count, "ACCOUNTS"),
            "sanctioned_amount": Measure(AdvanceMonthlyFact.sanctioned_amount, "INR"),
            "disbursed_amount": Measure(AdvanceMonthlyFact.disbursed_amount, "INR"),
            "overdue_amount": Measure(AdvanceMonthlyFact.overdue_amount, "INR"),
        },
    ),
    "NPA_SMA": SemanticDataset(
        AssetQualityMonthlyFact, AssetQualityMonthlyFact.classification,
        frozenset({"SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"}),
        {
            "outstanding_amount": Measure(AssetQualityMonthlyFact.outstanding_amount, "INR"),
            "account_count": Measure(AssetQualityMonthlyFact.account_count, "ACCOUNTS"),
            "slippage_amount": Measure(AssetQualityMonthlyFact.slippage_amount, "INR"),
            "recovery_amount": Measure(AssetQualityMonthlyFact.recovery_amount, "INR"),
            "target_recovery_amount": Measure(AssetQualityMonthlyFact.target_recovery_amount, "INR"),
        },
    ),
    "DIGITAL": SemanticDataset(
        DigitalProductMonthlyFact, DigitalProductMonthlyFact.product_type,
        frozenset({"MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"}),
        {
            "eligible_customer_count": Measure(DigitalProductMonthlyFact.eligible_customer_count, "CUSTOMERS"),
            "registered_customer_count": Measure(DigitalProductMonthlyFact.registered_customer_count, "CUSTOMERS"),
            "active_customer_count": Measure(DigitalProductMonthlyFact.active_customer_count, "CUSTOMERS"),
            "transaction_count": Measure(DigitalProductMonthlyFact.transaction_count, "TRANSACTIONS"),
            "transaction_amount": Measure(DigitalProductMonthlyFact.transaction_amount, "INR"),
            "target_registered_count": Measure(DigitalProductMonthlyFact.target_registered_count, "CUSTOMERS"),
            "target_transaction_count": Measure(DigitalProductMonthlyFact.target_transaction_count, "TRANSACTIONS"),
        },
    ),
}
