from dataclasses import dataclass
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.organization import OrganizationHierarchy, OrganizationUnit
from backend.repositories.users import UserAccessRecord


ROLE_OFFICE_TYPE = {
    "HO_USER": "HO",
    "CO_USER": "CO",
    "RO_USER": "RO",
    "BRANCH_USER": "BRANCH",
}


class ScopeConfigurationError(Exception):
    """Raised when a user's role and assigned office are inconsistent."""


class OrganizationAccessDenied(Exception):
    """Raised when a requested organization is outside the user's hierarchy."""


_BANK_WIDE_PATTERNS = (
    re.compile(r"\bbank\s+as\s+(?:a\s+)?whole\b", re.IGNORECASE),
    re.compile(r"\b(?:the\s+)?(?:entire|whole)\s+bank\b", re.IGNORECASE),
    re.compile(r"\bbank[\s-]?wide\b", re.IGNORECASE),
    re.compile(r"\bacross\s+(?:the\s+)?bank\b", re.IGNORECASE),
)


def requests_bank_wide_scope(message: str) -> bool:
    """Detect an explicit request to expand analytics to the entire bank."""
    return any(pattern.search(message) for pattern in _BANK_WIDE_PATTERNS)


@dataclass(frozen=True)
class ScopedOrganization:
    id: int
    code: str
    name: str
    office_type: str
    parent_id: int | None
    depth: int


@dataclass(frozen=True)
class ResolvedOrganizationScope:
    user_id: int
    role: str
    assigned_root_id: int
    effective_root_id: int
    organizations: tuple[ScopedOrganization, ...]

    @property
    def organization_ids(self) -> tuple[int, ...]:
        return tuple(organization.id for organization in self.organizations)


def organization_ids_subquery(root_organization_id: int):
    """Return a reusable SQL subquery for mandatory business-data filtering."""
    return select(OrganizationHierarchy.descendant_id).where(
        OrganizationHierarchy.ancestor_id == root_organization_id
    )


async def resolve_organization_scope(
    session: AsyncSession,
    access: UserAccessRecord,
    requested_organization_id: int | None = None,
) -> ResolvedOrganizationScope:
    expected_office_type = ROLE_OFFICE_TYPE.get(access.role_code)
    if expected_office_type is None or expected_office_type != access.office_type:
        raise ScopeConfigurationError("Role and primary office assignment do not match")

    effective_root_id = access.organization_unit_id
    if requested_organization_id is not None:
        permitted = await session.scalar(
            select(OrganizationHierarchy.ancestor_id).where(
                OrganizationHierarchy.ancestor_id == access.organization_unit_id,
                OrganizationHierarchy.descendant_id == requested_organization_id,
            )
        )
        if permitted is None:
            raise OrganizationAccessDenied
        effective_root_id = requested_organization_id

    statement = (
        select(
            OrganizationUnit.id,
            OrganizationUnit.code,
            OrganizationUnit.name,
            OrganizationUnit.office_type,
            OrganizationUnit.parent_id,
            OrganizationHierarchy.depth,
        )
        .join(
            OrganizationHierarchy,
            OrganizationHierarchy.descendant_id == OrganizationUnit.id,
        )
        .where(
            OrganizationHierarchy.ancestor_id == effective_root_id,
            OrganizationUnit.is_active.is_(True),
        )
        .order_by(OrganizationHierarchy.depth, OrganizationUnit.code)
    )
    rows = (await session.execute(statement)).all()
    if not rows:
        raise ScopeConfigurationError("No active organizations found for assigned scope")

    organizations = tuple(
        ScopedOrganization(
            id=row.id,
            code=row.code,
            name=row.name,
            office_type=row.office_type.value,
            parent_id=row.parent_id,
            depth=row.depth,
        )
        for row in rows
    )
    return ResolvedOrganizationScope(
        user_id=access.user.id,
        role=access.role_code,
        assigned_root_id=access.organization_unit_id,
        effective_root_id=effective_root_id,
        organizations=organizations,
    )
