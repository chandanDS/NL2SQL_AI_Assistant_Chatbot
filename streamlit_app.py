import os

import httpx
import streamlit as st
from dotenv import load_dotenv


load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="Banking NL2SQL assistant",
    page_icon=":material/account_balance:",
    layout="wide",
)

st.title("Banking NL2SQL assistant")
st.caption("Local proof-of-concept foundation")

st.session_state.setdefault("access_token", None)
st.session_state.setdefault("current_user", None)


def logout() -> None:
    st.session_state.access_token = None
    st.session_state.current_user = None


def load_current_user() -> dict | None:
    token = st.session_state.access_token
    if not token:
        return None
    try:
        response = httpx.get(
            f"{API_BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 401:
            logout()
        return None
    except httpx.HTTPError:
        return None


if st.session_state.access_token:
    st.session_state.current_user = load_current_user()

if not st.session_state.current_user:
    with st.container(border=True):
        st.subheader("Sign in")
        st.caption("Use one of the synthetic banking staff accounts.")
        with st.form("login_form", border=False):
            username = st.text_input(
                "Username",
                placeholder="bankuser0001",
                key="login_username",
            )
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button(
                "Sign in",
                type="primary",
                icon=":material/login:",
            )

        if submitted:
            try:
                response = httpx.post(
                    f"{API_BASE_URL}/auth/login",
                    data={"username": username, "password": password},
                    timeout=10.0,
                )
                if response.status_code == 401:
                    st.error("Invalid username or password.")
                else:
                    response.raise_for_status()
                    st.session_state.access_token = response.json()["access_token"]
                    st.rerun()
            except httpx.HTTPError:
                st.error("Authentication service is unavailable. Start FastAPI and retry.")
    st.stop()

user = st.session_state.current_user
with st.sidebar:
    st.subheader(user["full_name"])
    st.caption(f'{user["role"]} · {user["organization_name"]}')
    st.button("Sign out", icon=":material/logout:", on_click=logout)

with st.container(border=True):
    st.subheader("Authenticated session")
    st.success("Password login and JWT validation succeeded.", icon=":material/verified_user:")
    st.write(f'**Employee ID:** {user["employee_id"]}')
    st.write(f'**Office:** {user["organization_code"]} — {user["organization_name"]}')
    st.write(f'**Scope:** {user["office_type"]}')
    if user["must_change_password"]:
        st.warning("This synthetic user is marked for a password change.")

st.info(
    "Authentication is active. NL2SQL chatbot functionality has not been added.",
    icon=":material/info:",
)
