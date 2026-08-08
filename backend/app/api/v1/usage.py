import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_organization_member
from app.models.organization import OrganizationMember
from app.schemas.usage import UsageDayResponse, UsageSummaryResponse
from app.repositories.usage_repository import UsageRepository
from app.services.usage_service import UsageService


router = APIRouter(
    prefix="/organizations/{organization_id}/usage",
    tags=["usage"],
)


@router.get("", response_model=UsageSummaryResponse)
def get_usage(
    organization_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    _membership: Annotated[
        OrganizationMember,
        Depends(require_organization_member),
    ],
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> UsageSummaryResponse:
    """What this workspace has spent, and what is left of today's budget.

    Readable by any member rather than owners only. A limit people cannot see
    is a limit that arrives as an unexplained error, and the numbers here are
    the workspace's own — there is nothing to protect from its members.
    """
    status = UsageService(db).status(organization_id)
    history = UsageRepository(db).list_recent(
        organization_id=organization_id,
        days=days,
    )
    return UsageSummaryResponse(
        used_tokens_today=status.used_tokens,
        daily_token_budget=status.limit_tokens,
        remaining_tokens_today=status.remaining_tokens,
        estimated_cost_usd_today=str(status.estimated_cost_usd),
        days=[
            UsageDayResponse(
                usage_date=row.usage_date,
                embedding_tokens=row.embedding_tokens,
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                total_tokens=row.total_tokens,
                chat_calls=row.chat_calls,
                embedding_calls=row.embedding_calls,
                estimated_cost_usd=str(row.estimated_cost_usd),
            )
            for row in history
        ],
    )
