from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class BackendError(Exception):
    status_code: int
    detail: str

    def __str__(self) -> str:
        return self.detail


class BankingApiClient:
    def __init__(self, base_url: str, timeout: float = 45.0):
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def _request(self, method: str, path: str, token: str | None = None, **kwargs) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            response = self._client.request(method, path, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise BackendError(503, "The local FastAPI service is not reachable.") from exc
        if response.is_error:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text or "Backend request failed"
            raise BackendError(response.status_code, str(detail))
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request("POST", "/auth/login", data={"username": username, "password": password})

    def me(self, token: str) -> dict[str, Any]:
        return self._request("GET", "/auth/me", token)

    def interpret(self, token: str, message: str, session_id: str | None) -> dict[str, Any]:
        payload: dict[str, Any] = {"message": message}
        if session_id:
            payload["session_id"] = session_id
        return self._request("POST", "/intent/interpret", token, json=payload)

    def query(self, token: str, analytics_request: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/analytics/query", token, json=analytics_request)

    def semantic_query(self, token: str, plan: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"plan": plan}
        if session_id:
            payload["session_id"] = session_id
        return self._request("POST", "/semantic/query", token, json=payload)

    def insights(self, token: str, analytics_request: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
        return self._request("POST", "/insights/generate", token, json={"analytics_request": analytics_request, "session_id": session_id})

    def sessions(self, token: str) -> dict[str, Any]:
        return self._request("GET", "/history/sessions", token)

    def messages(self, token: str, session_id: str) -> dict[str, Any]:
        return self._request("GET", f"/history/sessions/{session_id}/messages", token)

    def usage(self, token: str, days: int) -> dict[str, Any]:
        return self._request("GET", "/usage/summary", token, params={"days": days})

    def audit(self, token: str, limit: int = 100) -> dict[str, Any]:
        return self._request("GET", "/audit/events", token, params={"limit": limit})
