from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel


class SessionSummary(BaseModel):
    id: UUID; preview: str; message_count: int; total_tokens: int; created_at: datetime; updated_at: datetime
class MessageView(BaseModel):
    id: int; role: str; content: str; structured_intent: dict | None; created_at: datetime
class SessionList(BaseModel):
    sessions: list[SessionSummary]
class MessageList(BaseModel):
    session_id: UUID; messages: list[MessageView]
class UsageDaily(BaseModel):
    day: date; operation: str; input_tokens: int; output_tokens: int; total_tokens: int; calls: int
class UsageSummary(BaseModel):
    input_tokens: int; output_tokens: int; total_tokens: int; calls: int; daily: list[UsageDaily]
class AuditView(BaseModel):
    id: int; user_id: int | None; event_type: str; outcome: str; resource: str; organization_unit_id: int | None; details: dict; created_at: datetime
class AuditList(BaseModel):
    events: list[AuditView]
