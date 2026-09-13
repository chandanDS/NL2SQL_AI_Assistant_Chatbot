import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.db.session import get_db_session
from backend.llm.client import get_openai_client
from backend.llm.intent_service import context_from_intent, extract_intent, token_breakdown, try_fast_intent
from backend.schemas.intent import IntentRequest, IntentResponse, IntentStatus, TokenUsage
from backend.sessions.repository import SessionAccessDenied, add_message, get_or_create_session, last_messages
from backend.observability.events import record_audit, record_usage
from backend.rbac.scope import requests_bank_wide_scope


router = APIRouter(prefix="/intent", tags=["LLM intent and clarification"])
logger = logging.getLogger(__name__)


@router.post("/interpret", response_model=IntentResponse)
async def interpret_message(
    request: IntentRequest,
    access: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> IntentResponse:
    user_id = access.user.id
    if requests_bank_wide_scope(request.message) and access.role_code != "HO_USER":
        record_audit(
            session,
            "SCOPE_DENIED",
            "DENIED",
            "/intent/interpret",
            user_id,
            access.organization_unit_id,
            {"reason": "bank_wide_scope_requires_ho"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank-wide analytics requires an HO user. Your query was not executed.",
        )
    try:
        conversation = await get_or_create_session(session, user_id, request.session_id)
    except SessionAccessDenied:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation session not found") from None

    await add_message(session, conversation.id, user_id, "user", request.message.strip())
    history = await last_messages(session, conversation.id, limit=4)
    model_messages = [{"role": item.role, "content": item.content} for item in history]

    fast_result = try_fast_intent(request.message)
    route = "deterministic_fast_path" if fast_result else "llm_semantic_planner"
    if fast_result:
        intent, analytics_request = fast_result
        usage = TokenUsage()
    else:
        try:
            intent, analytics_request, usage = await extract_intent(
                get_openai_client(), model_messages, conversation.structured_context
            )
        except RuntimeError as exc:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
        except (APIError, ValueError):
            await session.rollback()
            logger.exception("intent_extraction_failed user_id=%s", user_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Intent service is temporarily unavailable") from None

    if intent.requested_scope.value == "bank_wide" and access.role_code != "HO_USER":
        record_audit(
            session,
            "SCOPE_DENIED",
            "DENIED",
            "/intent/interpret",
            user_id,
            access.organization_unit_id,
            {"reason": "bank_wide_scope_requires_ho"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bank-wide analytics requires an HO user. Your query was not executed.",
        )

    conversation.structured_context = context_from_intent(intent)
    assistant_text = intent.clarification_question or intent.interpretation
    await add_message(
        session, conversation.id, user_id, "assistant", assistant_text,
        structured_intent=intent.model_dump(mode="json"),
    )
    record_usage(session, user_id, "intent", usage, conversation.id)
    record_audit(session, "INTENT", "SUCCESS", "/intent/interpret", user_id, access.organization_unit_id,
                 {"session_id": str(conversation.id), "status": intent.status, "kpi": intent.kpi_code, "route": route})
    await session.commit()

    logger.info(
        "intent_extracted user_id=%s session_id=%s status=%s kpi=%s confidence=%.2f missing=%s tokens=%s",
        user_id, conversation.id, intent.status, intent.kpi_code,
        intent.confidence, intent.missing_fields, usage.total_tokens,
    )
    return IntentResponse(
        session_id=conversation.id,
        status=intent.status,
        intent=intent,
        clarification_question=intent.clarification_question if intent.status == IntentStatus.NEEDS_CLARIFICATION else None,
        analytics_request=analytics_request,
        dynamic_query_plan=intent.dynamic_query_plan,
        messages_used=len(history),
        usage=usage,
        usage_breakdown=token_breakdown(
            usage,
            request.message.strip(),
            model_messages[:-1],
            dynamic_sql_plan=intent.dynamic_query_plan is not None,
        ),
    )
