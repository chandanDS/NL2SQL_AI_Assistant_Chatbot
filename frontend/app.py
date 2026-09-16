from __future__ import annotations

import os
from uuid import uuid4

import streamlit as st
import pandas as pd

from frontend.api_client.client import BackendError, BankingApiClient
from frontend.components.results import render_result, render_semantic_result
from frontend.prediction_followups import prediction_followups


st.set_page_config(page_title="Banking Data Intelligence Assistant", page_icon=":material/account_balance:", layout="wide")
st.logo("frontend/static/canara-bank-logo.webp", size="large")

st.html("""
<style>
.stApp {
    background:
        linear-gradient(rgba(255, 255, 255, 0.20), rgba(244, 250, 255, 0.28)),
        url("app/static/canara-light-background.png") center / cover fixed;
}
[data-testid="stMainBlockContainer"] {
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(181, 218, 240, 0.70);
    border-radius: 18px;
    box-shadow: 0 16px 44px rgba(28, 101, 145, 0.12);
    backdrop-filter: blur(8px);
    margin-top: 1.25rem;
    margin-bottom: 1.25rem;
}
[data-testid="stSidebar"] {
    background: rgba(0, 103, 168, 0.97);
    backdrop-filter: blur(10px);
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 0.65rem;
    padding-bottom: 0.5rem;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.4rem;
}
[data-testid="stSidebar"] .stButton button {
    min-height: 2.25rem;
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
}
.canara-brand-strip {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    min-height: 72px;
    padding: 10px 22px;
    margin: -0.25rem 0 1.35rem 0;
    border-radius: 12px;
    border-bottom: 3px solid #FFD54A;
    background: linear-gradient(105deg, #087DBD 0%, #0067A8 72%, #00578F 100%);
    box-shadow: 0 8px 22px rgba(0, 91, 148, 0.15);
}
.canara-brand-strip img {
    display: block;
    width: min(390px, 72vw);
    max-height: 58px;
    object-fit: contain;
}
</style>
""")


def brand_banner() -> None:
    st.html("""
    <div class="canara-brand-strip">
        <img src="app/static/canara-bank-logo.webp" alt="Canara Bank — Together We Can">
    </div>
    """)


@st.cache_resource
def api_client() -> BankingApiClient:
    return BankingApiClient(os.getenv("BANKING_API_URL", "http://127.0.0.1:8000"))


def initialize_state() -> None:
    defaults = {
        "access_token": None,
        "current_user": None,
        "conversation_id": None,
        "messages": [],
        "pending_clarification": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def logout() -> None:
    for key in ("access_token", "current_user", "conversation_id", "messages", "pending_clarification"):
        st.session_state[key] = None if key != "messages" else []
    st.session_state.pop("sidebar_usage_query", None)


def login_page() -> None:
    brand_banner()
    st.title("Banking Data Intelligence Assistant")
    st.caption("Secure, role-aware analytics for deposits, advances, NPA/SMA and digital products")
    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        with st.form("login_form", border=True):
            st.subheader("Sign in")
            username = st.text_input("Username", autocomplete="username")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch")
        if submitted:
            if not username.strip() or not password:
                st.warning("Enter both username and password.")
                return
            try:
                token = api_client().login(username.strip(), password)["access_token"]
                user = api_client().me(token)
            except BackendError as exc:
                st.error(exc.detail)
                return
            st.session_state.access_token = token
            st.session_state.current_user = user
            st.rerun()


def assistant_summary(result: dict) -> str:
    label = result["kpi_code"].replace("_", " ").title()
    comparison = result["comparison"].upper()
    text = f"Here is **{label}** for {result['period_start']} to {result['period_end']}."
    if comparison != "NONE" and result.get("growth_percent") is not None:
        text += f" The {comparison} change is **{float(result['growth_percent']):,.2f}%**."
    return text


def process_message(message: str) -> None:
    st.session_state.messages.append({"id": str(uuid4()), "role": "user", "content": message})
    try:
        interpreted = api_client().interpret(
            st.session_state.access_token, message, st.session_state.conversation_id
        )
        st.session_state.conversation_id = interpreted["session_id"]
        if interpreted["status"] == "ready":
            if interpreted.get("analytics_request"):
                insight_response = api_client().insights(st.session_state.access_token, interpreted["analytics_request"], st.session_state.conversation_id)
                result = insight_response["result"]
                st.session_state.messages.append({
                    "id": str(uuid4()), "role": "assistant", "content": assistant_summary(result),
                    "query": message,
                    "result": result, "intent": interpreted["intent"], "usage": interpreted["usage"],
                    "usage_breakdown": interpreted["usage_breakdown"],
                    "insights": insight_response["insights"], "follow_ups": insight_response["follow_ups"],
                    "insight_usage": insight_response["usage"], "empty_result": insight_response["empty_result"],
                })
            elif interpreted.get("dynamic_query_plan"):
                result = api_client().semantic_query(
                    st.session_state.access_token,
                    interpreted["dynamic_query_plan"],
                    st.session_state.conversation_id,
                )
                grounded_answer = result["insights"][0] if result.get("insights") else result["interpretation"]
                st.session_state.messages.append({
                    "id": str(uuid4()), "role": "assistant", "content": grounded_answer,
                    "query": message, "semantic_result": result, "intent": interpreted["intent"],
                    "usage": interpreted["usage"], "usage_breakdown": interpreted["usage_breakdown"],
                    "insights": result.get("insights", [])[1:], "follow_ups": [],
                    "insight_usage": result.get("insight_usage", {"total_tokens": 0}),
                    "empty_result": result["row_count"] == 0,
                })
            else:
                raise BackendError(422, "The interpreted request has no executable query plan.")
            st.session_state.pending_clarification = None
        elif interpreted["status"] == "needs_clarification":
            question = interpreted["clarification_question"] or "Please provide the missing details."
            st.session_state.messages.append({"id": str(uuid4()), "role": "assistant", "content": question})
            st.session_state.pending_clarification = interpreted
        else:
            explanation = interpreted["intent"].get("interpretation") or "That metric is not supported by the current banking dataset."
            st.session_state.messages.append({"id": str(uuid4()), "role": "assistant", "content": explanation})
            st.session_state.pending_clarification = None
    except BackendError as exc:
        if exc.status_code == 401:
            logout()
            st.error("Your session expired. Please sign in again.")
        else:
            st.session_state.messages.append({"id": str(uuid4()), "role": "assistant", "content": f"I could not complete that request: {exc.detail}"})


def chatbot_page() -> None:
    st.title("Banking Data Intelligence Assistant")
    st.caption("Ask about balances, accounts, targets, YoY/QoQ changes, recoveries and digital activity.")

    if not st.session_state.messages:
        suggestions = {
            "CASA accounts": "Show my CASA account count for March 2026 compared with last year",
            "Advance gap": "Show advance outstanding gap to target for Q1 2026",
            "NPA recovery": "Show NPA and SMA recovery amount for March 2026",
        }
        selected = st.pills("Try asking", list(suggestions), label_visibility="collapsed")
        if selected:
            process_message(suggestions[selected])
            st.rerun()

    for item in st.session_state.messages:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item.get("empty_result"):
                st.info("No data matched this KPI, period, product selection, and permitted organization scope.")
            elif item.get("result"):
                render_result(item["result"], item["id"])
            elif item.get("semantic_result"):
                render_semantic_result(item["semantic_result"], item["id"])
            if item.get("insights"):
                st.markdown("**Grounded insights**")
                for insight in item["insights"]:
                    st.markdown(f"- {insight}")
            if item.get("follow_ups"):
                st.caption("Suggested follow-ups")
                with st.container(horizontal=True):
                    for index, suggestion in enumerate(item["follow_ups"]):
                        if st.button(suggestion["label"], key=f"followup_{item['id']}_{index}"):
                            process_message(suggestion["question"])
                            st.rerun()
    if prompt := st.chat_input("Ask a banking KPI question", max_chars=2_000, submit_mode="disable"):
        process_message(prompt)
        st.rerun()


def history_page() -> None:
    st.title("Session history")
    st.caption("Your persisted chatbot conversations")
    try:
        sessions = api_client().sessions(st.session_state.access_token)["sessions"]
    except BackendError as exc:
        st.error(exc.detail); return
    if not sessions:
        st.info("No saved conversations yet."); return
    frame = pd.DataFrame(sessions)
    st.dataframe(frame[["preview", "message_count", "total_tokens", "updated_at"]], hide_index=True,
                 column_config={"preview":"Conversation", "message_count":"Messages", "total_tokens":"Tokens", "updated_at":st.column_config.DatetimeColumn("Updated")})
    labels = {f"{x['preview']} · {x['updated_at'][:10]}": x["id"] for x in sessions}
    selected = st.selectbox("Open conversation", list(labels), key="history_session")
    try:
        messages = api_client().messages(st.session_state.access_token, labels[selected])["messages"]
    except BackendError as exc:
        st.error(exc.detail); return
    for item in messages:
        with st.chat_message(item["role"]): st.markdown(item["content"])


def usage_page() -> None:
    st.title("Token usage")
    days = st.segmented_control("Period", [7, 30, 90], default=30, format_func=lambda x: f"{x} days", key="usage_days")
    try:
        usage = api_client().usage(st.session_state.access_token, int(days or 30))
    except BackendError as exc:
        st.error(exc.detail); return
    with st.container(horizontal=True):
        st.metric("Total tokens", f"{usage['total_tokens']:,}", border=True)
        st.metric("Input tokens", f"{usage['input_tokens']:,}", border=True)
        st.metric("Output tokens", f"{usage['output_tokens']:,}", border=True)
        st.metric("LLM calls", f"{usage['calls']:,}", border=True)
    if usage["daily"]:
        frame=pd.DataFrame(usage["daily"]); frame["day"]=pd.to_datetime(frame["day"])
        st.bar_chart(frame, x="day", y="total_tokens", color="operation")
        st.dataframe(frame, hide_index=True)
    else: st.info("No token usage was recorded in this period.")


def audit_page() -> None:
    st.title("Audit log")
    st.caption("HO-only security and analytics activity")
    try:
        events=api_client().audit(st.session_state.access_token)["events"]
    except BackendError as exc:
        st.error(exc.detail); return
    if not events: st.info("No audit events have been recorded yet."); return
    frame=pd.DataFrame(events)
    st.dataframe(frame, hide_index=True, column_config={"created_at":st.column_config.DatetimeColumn("Time"), "details":st.column_config.JsonColumn("Details")})


def ai_ml_page() -> None:
    st.title("AI/ML prediction output")
    st.caption("Synthetic model-output data. Your existing HO/CO/RO/branch access scope applies.")
    st.info("AI/ML Prediction Output Referred from stored table")
    st.session_state.setdefault("ml_lead_question", None)
    st.session_state.setdefault("ml_lead_result", None)
    st.session_state.setdefault("ml_lead_page", 1)
    st.session_state.setdefault("ml_lead_export", None)

    def run_prediction(question: str) -> None:
        st.session_state.ml_lead_question = question
        st.session_state.ml_lead_page = 1
        st.session_state.ml_lead_export = None
        try:
            st.session_state.ml_lead_result = api_client().ml_leads(st.session_state.access_token, question)
        except BackendError as exc:
            st.session_state.ml_lead_result = None
            st.error(exc.detail)

    prediction_modules = {
        "Campaign hot leads": "What are the hot personal loan leads for Mumbai branch?",
        "Risk scorecard": "Who are the risky customers in my branch?",
        "ML underwriting": "Show pre-approved personal loan customers in my branch",
        "PL propensity": "Show PL propensity bands in my branch",
        "Risk-tag review": "Show good customers tagged as bad by the risk team in my branch",
    }
    selected_module = st.selectbox(
        "Prediction Module",
        ["Select a prediction module", *prediction_modules],
        key="ml_prediction_module",
    )
    if st.button("Prediction Output", disabled=selected_module == "Select a prediction module"):
        run_prediction(prediction_modules[selected_module])

    if question := st.chat_input("Ask about PL campaign, propensity, underwriting or risk leads", key="ml_chat_input", submit_mode="disable"):
        run_prediction(question)

    result = st.session_state.ml_lead_result
    if result is None:
        return
    total_pages = max(1, (result["total_count"] + 99) // 100)
    page_number = st.number_input("Result page", min_value=1, max_value=total_pages, value=st.session_state.ml_lead_page, step=1)
    if page_number != st.session_state.ml_lead_page:
        st.session_state.ml_lead_page = page_number
        try:
            result = api_client().ml_leads(st.session_state.access_token, st.session_state.ml_lead_question, offset=(page_number - 1) * 100)
            st.session_state.ml_lead_result = result
        except BackendError as exc:
            st.error(exc.detail)
            return
    with st.chat_message("user"):
        st.write(st.session_state.ml_lead_question)
    with st.chat_message("assistant"):
        st.markdown(f"**{result['total_count']:,} {result['title'].lower()}** in **{result['organization']}**.")
        st.caption(f"Source: {result['source_table']} · Synthetic data · {result['guidance']}")
        if result.get("band_counts"):
            st.table(pd.DataFrame(
                [{"Propensity band": band.replace("_", " ").title(), "Customers": count}
                 for band, count in result["band_counts"].items()]
            ))
        if result["records"]:
            st.dataframe(pd.DataFrame(result["records"]), hide_index=True, height=420)
        else:
            st.info("No matching synthetic leads were found in your permitted scope.")
    if result["total_count"]:
        if st.button("Prepare full Excel download", icon=":material/download:"):
            try:
                with st.spinner("Preparing all permitted rows..."):
                    st.session_state.ml_lead_export = api_client().export_ml_leads(st.session_state.access_token, st.session_state.ml_lead_question)
            except BackendError as exc:
                st.error(exc.detail)
        if st.session_state.ml_lead_export:
            st.download_button(
                "Download all matching leads (.xlsx)",
                data=st.session_state.ml_lead_export,
                file_name=f"synthetic_pl_{result['use_case']}_leads.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                icon=":material/download:",
            )

    followups = prediction_followups(result["organization"])
    selected_followup = st.selectbox(
        "Next prediction output",
        ["Select a follow-up question", *followups],
        key="ml_followup_selection",
    )
    followup_submitted = st.button(
        "Run follow-up",
        disabled=selected_followup == "Select a follow-up question",
        icon=":material/arrow_forward:",
    )
    if followup_submitted and selected_followup in followups:
        run_prediction(followups[selected_followup])
        st.rerun()
    st.caption("Or type your own follow-up in the question box below.")


def sidebar_query_usage() -> None:
    usage_items = [item for item in st.session_state.messages if item.get("usage")]
    if not usage_items:
        st.caption("Token usage will appear here after your first query.")
        return

    selected_index = st.selectbox(
        "Token usage by query",
        options=range(len(usage_items)),
        index=len(usage_items) - 1,
        format_func=lambda index: f"{index + 1}. {usage_items[index].get('query', 'Banking query')[:32]}",
        key="sidebar_usage_query",
    )
    item = usage_items[selected_index]
    breakdown = item.get("usage_breakdown", {})
    insight_tokens = item.get("insight_usage", {}).get("total_tokens", 0)
    overall = breakdown.get("overall_tokens", item["usage"]["total_tokens"]) + insight_tokens
    token_table = pd.DataFrame([
        {"Stage": "User input", "Tokens": breakdown.get("user_input_tokens", 0)},
        {"Stage": "Routing and intent", "Tokens": breakdown.get("routing_tokens", item["usage"]["total_tokens"])},
        {"Stage": "Dynamic SQL planning", "Tokens": breakdown.get("sql_generation_tokens", 0)},
        {"Stage": "Context history", "Tokens": breakdown.get("context_history_tokens", 0)},
        {"Stage": "AI insight", "Tokens": insight_tokens},
        {"Stage": "Overall", "Tokens": overall},
    ])
    st.dataframe(
        token_table,
        height=188,
        row_height=25,
        hide_index=True,
        column_config={
            "Stage": st.column_config.TextColumn("Stage"),
            "Tokens": st.column_config.NumberColumn("Tokens", format="%d"),
        },
    )
    with st.popover("About token counts", icon=":material/info:"):
        st.caption(
            "Overall is the exact API-reported total. Stage allocations are estimates. "
            "Dynamic SQL planning represents structured-plan output tokens; SQLAlchemy compilation itself uses zero LLM tokens."
        )


def authenticated_app() -> None:
    chat_page = st.Page(chatbot_page, title="Chat", icon=":material/chat:", default=True)
    pages = {
        "Assistant": [
            chat_page,
            st.Page(ai_ml_page, title="AI/ML prediction output", icon=":material/target:"),
            st.Page(history_page, title="Session history", icon=":material/history:"),
        ]
    }
    if st.session_state.current_user["role"] == "HO_USER":
        pages["Administration"] = [
            st.Page(audit_page, title="Audit log", icon=":material/policy:"),
        ]
    page = st.navigation(pages, position="sidebar", expanded=True)
    brand_banner()

    user = st.session_state.current_user
    with st.sidebar:
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"{user['role']} · {user['organization_code']} · {user['office_type']}")
        with st.container(horizontal=True, gap="small"):
            if st.button("New", icon=":material/add_comment:", width="stretch"):
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.session_state.pending_clarification = None
                st.session_state.pop("sidebar_usage_query", None)
                st.switch_page(chat_page)
            if st.button("Sign out", icon=":material/logout:", width="stretch"):
                logout()
                st.rerun()
        sidebar_query_usage()
        st.caption(":material/security: Access restricted to your assigned organization hierarchy.")

    page.run()


initialize_state()
if st.session_state.access_token:
    authenticated_app()
else:
    login_page()
