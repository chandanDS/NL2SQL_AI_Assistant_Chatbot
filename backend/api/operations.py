from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.db.session import get_db_session
from backend.models.conversation import ConversationMessage, ConversationSession
from backend.models.observability import AuditEvent, TokenUsageEvent
from backend.schemas.operations import AuditList, AuditView, MessageList, MessageView, SessionList, SessionSummary, UsageDaily, UsageSummary


router = APIRouter(tags=["history, usage and audit"])


@router.get("/history/sessions", response_model=SessionList)
async def sessions(access: CurrentUser, db: Annotated[AsyncSession, Depends(get_db_session)], limit: Annotated[int, Query(ge=1, le=100)] = 50):
    rows = (await db.scalars(select(ConversationSession).where(ConversationSession.user_id == access.user.id).order_by(ConversationSession.updated_at.desc()).limit(limit))).all()
    output=[]
    for item in rows:
        messages=(await db.scalars(select(ConversationMessage).where(ConversationMessage.session_id == item.id).order_by(ConversationMessage.id))).all()
        tokens=await db.scalar(select(func.coalesce(func.sum(TokenUsageEvent.total_tokens),0)).where(TokenUsageEvent.session_id == item.id))
        preview=next((m.content for m in messages if m.role == "user"), "New conversation")
        output.append(SessionSummary(id=item.id, preview=preview[:120], message_count=len(messages), total_tokens=tokens or 0, created_at=item.created_at, updated_at=item.updated_at))
    return SessionList(sessions=output)


@router.get("/history/sessions/{session_id}/messages", response_model=MessageList)
async def messages(session_id: UUID, access: CurrentUser, db: Annotated[AsyncSession, Depends(get_db_session)]):
    owned=await db.scalar(select(ConversationSession.id).where(ConversationSession.id == session_id, ConversationSession.user_id == access.user.id))
    if owned is None: raise HTTPException(status_code=404, detail="Conversation session not found")
    rows=(await db.scalars(select(ConversationMessage).where(ConversationMessage.session_id == session_id).order_by(ConversationMessage.id))).all()
    return MessageList(session_id=session_id, messages=[MessageView(id=x.id,role=x.role,content=x.content,structured_intent=x.structured_intent,created_at=x.created_at) for x in rows])


@router.get("/usage/summary", response_model=UsageSummary)
async def usage(access: CurrentUser, db: Annotated[AsyncSession, Depends(get_db_session)], days: Annotated[int, Query(ge=1, le=365)] = 30):
    since=datetime.now(timezone.utc)-timedelta(days=days)
    statement=(select(func.date(TokenUsageEvent.created_at),TokenUsageEvent.operation,func.sum(TokenUsageEvent.input_tokens),func.sum(TokenUsageEvent.output_tokens),func.sum(TokenUsageEvent.total_tokens),func.count(TokenUsageEvent.id)).where(TokenUsageEvent.user_id==access.user.id,TokenUsageEvent.created_at>=since).group_by(func.date(TokenUsageEvent.created_at),TokenUsageEvent.operation).order_by(func.date(TokenUsageEvent.created_at)))
    rows=(await db.execute(statement)).all(); daily=[UsageDaily(day=r[0],operation=r[1],input_tokens=r[2],output_tokens=r[3],total_tokens=r[4],calls=r[5]) for r in rows]
    return UsageSummary(input_tokens=sum(x.input_tokens for x in daily),output_tokens=sum(x.output_tokens for x in daily),total_tokens=sum(x.total_tokens for x in daily),calls=sum(x.calls for x in daily),daily=daily)


@router.get("/audit/events", response_model=AuditList)
async def audit(access: CurrentUser, db: Annotated[AsyncSession, Depends(get_db_session)], limit: Annotated[int, Query(ge=1,le=500)] = 100):
    if access.role_code != "HO_USER": raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="HO role required")
    rows=(await db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit))).all()
    return AuditList(events=[AuditView(id=x.id,user_id=x.user_id,event_type=x.event_type,outcome=x.outcome,resource=x.resource,organization_unit_id=x.organization_unit_id,details=x.details,created_at=x.created_at) for x in rows])
