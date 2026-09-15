"""Streamlit Community Cloud entry point.

Community Cloud starts one Streamlit command, so this entry point starts the
existing FastAPI application on localhost once per worker and then renders the
existing Streamlit frontend.
"""

from __future__ import annotations

import runpy
from pathlib import Path

from frontend.cloud_runtime import start_embedded_api


start_embedded_api()

# Execute the UI as the active Streamlit script. This is more reliable than a
# module import on Community Cloud, where imported page modules can be retained
# across script reruns without replaying their top-level Streamlit commands.
runpy.run_path(str(Path(__file__).parent / "frontend" / "app.py"), run_name="__main__")
