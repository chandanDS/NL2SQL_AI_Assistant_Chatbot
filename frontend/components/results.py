from __future__ import annotations

from decimal import Decimal

import pandas as pd
import streamlit as st


def _number(value) -> float | None:
    return float(Decimal(str(value))) if value is not None else None


def format_value(value, unit: str) -> str:
    number = _number(value)
    if number is None:
        return "Not applicable"
    if unit == "INR":
        return f"₹{number / 10_000_000:,.2f} Cr"
    return f"{number:,.2f}"


def result_dataframe(result: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "KPI": result["kpi_code"].replace("_", " ").title(),
            "Actual": _number(result["actual_value"]),
            "Target": _number(result.get("target_value")),
            "Gap to target": _number(result.get("gap_to_target")),
            "Shortfall": _number(result.get("shortfall_to_target")),
            "Achievement %": _number(result.get("achievement_percent")),
            "Comparison value": _number(result.get("comparison_value")),
            "Growth %": _number(result.get("growth_percent")),
            "Unit": result["unit"],
            "Period start": result["period_start"],
            "Period end": result["period_end"],
        }]
    )


def render_result(result: dict, key_suffix: str) -> None:
    unit = result["unit"]
    comparison = result["comparison"].upper()
    growth = _number(result.get("growth_percent"))
    achievement = _number(result.get("achievement_percent"))
    with st.container(horizontal=True):
        st.metric("Actual", format_value(result["actual_value"], unit), border=True)
        st.metric("Target", format_value(result.get("target_value"), unit), border=True)
        st.metric("Gap to target", format_value(result.get("gap_to_target"), unit), border=True)
        st.metric(
            f"{comparison} growth" if comparison != "NONE" else "Achievement",
            f"{growth:,.2f}%" if growth is not None else (
                f"{achievement:,.2f}%" if achievement is not None else "Not applicable"
            ),
            border=True,
        )

    frame = result_dataframe(result)
    st.dataframe(
        frame,
        hide_index=True,
        column_config={
            "Actual": st.column_config.NumberColumn(format="%.2f"),
            "Target": st.column_config.NumberColumn(format="%.2f"),
            "Gap to target": st.column_config.NumberColumn(format="%.2f"),
            "Shortfall": st.column_config.NumberColumn(format="%.2f"),
            "Achievement %": st.column_config.NumberColumn(format="%.2f%%"),
            "Comparison value": st.column_config.NumberColumn(format="%.2f"),
            "Growth %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    if result.get("generated_sql"):
        with st.expander("Generated SQL (development only)", icon=":material/code:"):
            st.caption("Read-only SQL executed after KPI validation and organization-scope enforcement.")
            for index, query in enumerate(result["generated_sql"], start=1):
                if len(result["generated_sql"]) > 1:
                    st.markdown(f"**Query {index}**")
                st.code(query, language="sql")

    st.download_button(
        "Download result as CSV",
        data=frame.to_csv(index=False).encode("utf-8"),
        file_name=f"{result['kpi_code'].lower()}_{result['period_end']}.csv",
        mime="text/csv",
        icon=":material/download:",
        key=f"download_{key_suffix}",
    )


def render_semantic_result(result: dict, key_suffix: str) -> None:
    if result["rows"]:
        frame = pd.DataFrame(result["rows"])
        st.dataframe(
            frame,
            hide_index=True,
            column_config={"value": st.column_config.NumberColumn("Value", format="%.2f")},
        )
        st.download_button(
            "Download result as CSV",
            data=frame.to_csv(index=False).encode("utf-8"),
            file_name=f"dynamic_{result['module'].lower()}_result.csv",
            mime="text/csv",
            icon=":material/download:",
            key=f"semantic_download_{key_suffix}",
        )
    else:
        st.info("No data matched this dynamic query and your permitted organization scope.")

    if result.get("generated_sql"):
        with st.expander("Generated SQL (development only)", icon=":material/code:"):
            st.caption("Dynamically compiled from a validated semantic plan with mandatory RBAC filtering.")
            st.code(result["generated_sql"], language="sql")
