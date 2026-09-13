from dataclasses import dataclass
from typing import Any

from backend.models.banking import (
    AdvanceMonthlyFact,
    AssetQualityMonthlyFact,
    DepositMonthlyFact,
    DigitalProductMonthlyFact,
)


@dataclass(frozen=True)
class KpiDefinition:
    code: str
    module: str
    model: type[Any]
    value_column: Any
    target_column: Any | None
    dimension_column: Any
    allowed_dimensions: frozenset[str]
    unit: str
    aggregation: str


def _definition(code, module, model, value, target, dimension, allowed, unit, aggregation="snapshot"):
    return KpiDefinition(code, module, model, value, target, dimension, frozenset(allowed), unit, aggregation)


KPI_DEFINITIONS = {
    item.code: item
    for item in (
        _definition("DEPOSIT_BUSINESS_AMOUNT", "DEPOSITS", DepositMonthlyFact, DepositMonthlyFact.business_amount, DepositMonthlyFact.target_amount, DepositMonthlyFact.product_type, {"CA", "SA"}, "INR"),
        _definition("DEPOSIT_ACCOUNT_COUNT", "DEPOSITS", DepositMonthlyFact, DepositMonthlyFact.account_count, DepositMonthlyFact.target_account_count, DepositMonthlyFact.product_type, {"CA", "SA"}, "ACCOUNTS"),
        _definition("DEPOSIT_NEW_ACCOUNTS", "DEPOSITS", DepositMonthlyFact, DepositMonthlyFact.new_accounts, None, DepositMonthlyFact.product_type, {"CA", "SA"}, "ACCOUNTS", "sum"),
        _definition("ADVANCE_OUTSTANDING_AMOUNT", "ADVANCES", AdvanceMonthlyFact, AdvanceMonthlyFact.outstanding_amount, AdvanceMonthlyFact.target_amount, AdvanceMonthlyFact.product_type, {"EL", "VL", "PL", "HL", "MSME", "AGRI"}, "INR"),
        _definition("ADVANCE_ACCOUNT_COUNT", "ADVANCES", AdvanceMonthlyFact, AdvanceMonthlyFact.account_count, AdvanceMonthlyFact.target_account_count, AdvanceMonthlyFact.product_type, {"EL", "VL", "PL", "HL", "MSME", "AGRI"}, "ACCOUNTS"),
        _definition("ADVANCE_DISBURSEMENT_AMOUNT", "ADVANCES", AdvanceMonthlyFact, AdvanceMonthlyFact.disbursed_amount, None, AdvanceMonthlyFact.product_type, {"EL", "VL", "PL", "HL", "MSME", "AGRI"}, "INR", "sum"),
        _definition("ASSET_QUALITY_OUTSTANDING_AMOUNT", "NPA_SMA", AssetQualityMonthlyFact, AssetQualityMonthlyFact.outstanding_amount, None, AssetQualityMonthlyFact.classification, {"SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"}, "INR"),
        _definition("ASSET_QUALITY_ACCOUNT_COUNT", "NPA_SMA", AssetQualityMonthlyFact, AssetQualityMonthlyFact.account_count, None, AssetQualityMonthlyFact.classification, {"SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"}, "ACCOUNTS"),
        _definition("ASSET_QUALITY_RECOVERY_AMOUNT", "NPA_SMA", AssetQualityMonthlyFact, AssetQualityMonthlyFact.recovery_amount, AssetQualityMonthlyFact.target_recovery_amount, AssetQualityMonthlyFact.classification, {"SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"}, "INR", "sum"),
        _definition("DIGITAL_REGISTERED_CUSTOMERS", "DIGITAL", DigitalProductMonthlyFact, DigitalProductMonthlyFact.registered_customer_count, DigitalProductMonthlyFact.target_registered_count, DigitalProductMonthlyFact.product_type, {"MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"}, "CUSTOMERS"),
        _definition("DIGITAL_ACTIVE_CUSTOMERS", "DIGITAL", DigitalProductMonthlyFact, DigitalProductMonthlyFact.active_customer_count, None, DigitalProductMonthlyFact.product_type, {"MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"}, "CUSTOMERS"),
        _definition("DIGITAL_TRANSACTION_COUNT", "DIGITAL", DigitalProductMonthlyFact, DigitalProductMonthlyFact.transaction_count, DigitalProductMonthlyFact.target_transaction_count, DigitalProductMonthlyFact.product_type, {"MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"}, "TRANSACTIONS", "sum"),
        _definition("DIGITAL_TRANSACTION_AMOUNT", "DIGITAL", DigitalProductMonthlyFact, DigitalProductMonthlyFact.transaction_amount, None, DigitalProductMonthlyFact.product_type, {"MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"}, "INR", "sum"),
    )
}
