from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.models.observability import AuditEvent, TokenUsageEvent
from backend.schemas.intent import TokenUsage


def record_usage(session: AsyncSession, user_id: int, operation: str, usage: TokenUsage, session_id: UUID | None = None) -> None:
    if usage.total_tokens <= 0:
        return
    session.add(TokenUsageEvent(user_id=user_id, session_id=session_id, operation=operation, model=get_settings().openai_model,
                                input_tokens=usage.input_tokens, output_tokens=usage.output_tokens, total_tokens=usage.total_tokens))


def record_audit(session: AsyncSession, event_type: str, outcome: str, resource: str, user_id: int | None = None,
                 organization_unit_id: int | None = None, details: dict | None = None) -> None:
    session.add(AuditEvent(user_id=user_id, event_type=event_type, outcome=outcome, resource=resource,
                           organization_unit_id=organization_unit_id, details=details or {}))
