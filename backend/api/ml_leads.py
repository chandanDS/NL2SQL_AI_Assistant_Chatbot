"""Authenticated AI/ML lead list and Excel export endpoints."""

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.dependencies import CurrentUser
from backend.db.session import get_db_session
from backend.ml.service import LeadIntentError, query_leads
from backend.observability.events import record_audit
from backend.rbac.scope import OrganizationAccessDenied, ScopeConfigurationError


router = APIRouter(prefix="/ml/leads", tags=["AI/ML personal-loan leads"])


class LeadQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    limit: int = Field(default=100, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


async def _run(request: LeadQuestion, access: CurrentUser, session: AsyncSession, export: bool) -> dict:
    try:
        result = await query_leads(session, access, request.question, limit=request.limit, offset=request.offset, export=export)
    except OrganizationAccessDenied:
        raise HTTPException(status_code=403, detail="Requested branch is outside your permitted organization scope") from None
    except ScopeConfigurationError:
        raise HTTPException(status_code=403, detail="No valid organization scope is assigned") from None
    except LeadIntentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    record_audit(session, "ML_LEAD_EXPORT" if export else "ML_LEAD_QUERY", "SUCCESS", "/ml/leads", access.user.id,
                 result["organization_id"], {"use_case": result["use_case"], "row_count": result["total_count"], "synthetic": True})
    await session.commit()
    return result


@router.post("/query")
async def leads_query(request: LeadQuestion, access: CurrentUser, session: Annotated[AsyncSession, Depends(get_db_session)]):
    return await _run(request, access, session, False)


def _safe_excel_value(value):
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


@router.post("/export")
async def leads_export(request: LeadQuestion, access: CurrentUser, session: Annotated[AsyncSession, Depends(get_db_session)]):
    result = await _run(request, access, session, True)
    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet("Synthetic PL leads")
    records = result["records"]
    columns = list(records[0]) if records else ["customer_ref", "customer_name", "branch", "as_of_date"]
    sheet.append(columns)
    for record in records:
        sheet.append([_safe_excel_value(record.get(key)) for key in columns])
    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    filename = f"synthetic_pl_{result['use_case']}_leads.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"},
    )
