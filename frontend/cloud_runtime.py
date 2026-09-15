"""Lifecycle helper for running FastAPI inside Streamlit Community Cloud."""

from __future__ import annotations

import os
import socket
import threading
import time

import uvicorn


API_HOST = "127.0.0.1"
API_PORT = int(os.getenv("BANKING_EMBEDDED_API_PORT", "8000"))
API_URL = f"http://{API_HOST}:{API_PORT}"
os.environ["BANKING_API_URL"] = API_URL

_lock = threading.Lock()
_server_thread: threading.Thread | None = None


def _port_is_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.2)
        return connection.connect_ex((API_HOST, API_PORT)) == 0


def start_embedded_api() -> threading.Thread | None:
    """Start one daemonized FastAPI server per Python worker."""
    global _server_thread

    with _lock:
        if _server_thread and _server_thread.is_alive():
            return _server_thread
        if _port_is_open():
            return None

        server = uvicorn.Server(
            uvicorn.Config(
                "backend.main:app",
                host=API_HOST,
                port=API_PORT,
                log_level="info",
                access_log=False,
            )
        )
        _server_thread = threading.Thread(
            target=server.run,
            name="embedded-fastapi",
            daemon=True,
        )
        _server_thread.start()

        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if _port_is_open():
                return _server_thread
            if not _server_thread.is_alive():
                break
            time.sleep(0.1)
        raise RuntimeError("The embedded FastAPI service could not be started.")
