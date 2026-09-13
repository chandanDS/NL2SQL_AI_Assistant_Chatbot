from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.conversation import ConversationMessage, ConversationSession


class SessionAccessDenied(Exception):
    pass


async def get_or_create_session(session: AsyncSession, user_id: int, session_id: UUID | None) -> ConversationSession:
    if session_id is not None:
        conversation = await session.scalar(select(ConversationSession).where(ConversationSession.id == session_id))
        if conversation is None or conversation.user_id != user_id or not conversation.is_active:
            raise SessionAccessDenied
        return conversation
    conversation = ConversationSession(user_id=user_id, structured_context={})
    session.add(conversation)
    await session.flush()
    return conversation


async def add_message(session: AsyncSession, conversation_id: UUID, user_id: int, role: str, content: str, structured_intent: dict | None = None) -> None:
    session.add(ConversationMessage(session_id=conversation_id, user_id=user_id, role=role, content=content, structured_intent=structured_intent))
    await session.flush()


async def last_messages(session: AsyncSession, conversation_id: UUID, limit: int = 4) -> list[ConversationMessage]:
    rows = (await session.scalars(
        select(ConversationMessage)
        .where(ConversationMessage.session_id == conversation_id)
        .order_by(ConversationMessage.created_at.desc(), ConversationMessage.id.desc())
        .limit(limit)
    )).all()
    return list(reversed(rows))
