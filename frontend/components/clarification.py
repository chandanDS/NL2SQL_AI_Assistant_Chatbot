from __future__ import annotations

from datetime import date

import streamlit as st


KPI_LABELS = {
    "Deposit business amount": ("DEPOSIT_BUSINESS_AMOUNT", ["CA", "SA"]),
    "Deposit account count": ("DEPOSIT_ACCOUNT_COUNT", ["CA", "SA"]),
    "New deposit accounts": ("DEPOSIT_NEW_ACCOUNTS", ["CA", "SA"]),
    "Advance outstanding amount": ("ADVANCE_OUTSTANDING_AMOUNT", ["EL", "VL", "PL", "HL", "MSME", "AGRI"]),
    "Advance account count": ("ADVANCE_ACCOUNT_COUNT", ["EL", "VL", "PL", "HL", "MSME", "AGRI"]),
    "Advance disbursement amount": ("ADVANCE_DISBURSEMENT_AMOUNT", ["EL", "VL", "PL", "HL", "MSME", "AGRI"]),
    "NPA/SMA outstanding amount": ("ASSET_QUALITY_OUTSTANDING_AMOUNT", ["SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"]),
    "NPA/SMA account count": ("ASSET_QUALITY_ACCOUNT_COUNT", ["SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"]),
    "Recovery amount": ("ASSET_QUALITY_RECOVERY_AMOUNT", ["SMA0", "SMA1", "SMA2", "SUBSTANDARD", "DOUBTFUL", "LOSS"]),
    "Registered digital customers": ("DIGITAL_REGISTERED_CUSTOMERS", ["MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"]),
    "Active digital customers": ("DIGITAL_ACTIVE_CUSTOMERS", ["MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"]),
    "Digital transaction count": ("DIGITAL_TRANSACTION_COUNT", ["MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"]),
    "Digital transaction amount": ("DIGITAL_TRANSACTION_AMOUNT", ["MOBILE_BANKING", "INTERNET_BANKING", "UPI", "DEBIT_CARD", "POS", "QR", "AEPS"]),
}


def clarification_controls(pending: dict) -> str | None:
    intent = pending["intent"]
    codes = [value[0] for value in KPI_LABELS.values()]
    current_code = intent.get("kpi_code")
    default_index = codes.index(current_code) if current_code in codes else 0

    with st.container(border=True):
        st.subheader("Complete the request")
        st.caption(pending.get("clarification_question") or "Choose the missing details.")
        selected_label = st.selectbox("KPI", list(KPI_LABELS), index=default_index, key="clarify_kpi")
        code, allowed_products = KPI_LABELS[selected_label]
        selected_products = st.multiselect("Products or classifications", allowed_products, key=f"clarify_products_{code}")
        chosen_dates = st.date_input(
            "Date range", value=(date.today().replace(day=1), date.today().replace(day=1)),
            key="clarify_dates",
        )
        comparison = st.segmented_control("Comparison", ["None", "YoY", "QoQ"], default="None", key="clarify_comparison")
        if st.button("Continue", type="primary", icon=":material/check:", key="submit_clarification"):
            if not isinstance(chosen_dates, (tuple, list)) or len(chosen_dates) != 2:
                st.warning("Select both a start and end date.")
                return None
            start, end = (value.replace(day=1) for value in chosen_dates)
            products = ", ".join(selected_products) if selected_products else "all supported products"
            return (
                f"Use KPI {code} for {products}, from {start.isoformat()} through {end.isoformat()}, "
                f"with {str(comparison or 'None').lower()} comparison."
            )
    return None
