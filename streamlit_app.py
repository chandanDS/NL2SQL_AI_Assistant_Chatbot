"""Streamlit Community Cloud entry point.

Community Cloud starts one Streamlit command, so this entry point starts the
existing FastAPI application on localhost once per worker and then renders the
existing Streamlit frontend.
"""

from __future__ import annotations

from frontend.cloud_runtime import start_embedded_api


start_embedded_api()

# Keep this import last: frontend.app calls st.set_page_config() before UI output.
from frontend import app as _frontend_app  # noqa: E402,F401
