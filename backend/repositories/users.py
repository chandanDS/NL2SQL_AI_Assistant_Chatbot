from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.identity import Role, User, UserOrganizationAssignment, UserRole
from backend.models.organization import OrganizationUnit


@dataclass(frozen=True)
class UserAccessRecord:
    user: User
    role_code: str
    organization_unit_id: int
    organization_code: str
    organization_name: str
    office_type: str


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    normalized_username = username.strip().lower()
    return await session.scalar(select(User).where(User.username == normalized_username))


async def get_user_access(session: AsyncSession, user_id: int) -> UserAccessRecord | None:
    statement = (
        select(
            User,
            Role.code,
            OrganizationUnit.id,
            OrganizationUnit.code,
            OrganizationUnit.name,
            OrganizationUnit.office_type,
        )
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .join(UserOrganizationAssignment, UserOrganizationAssignment.user_id == User.id)
        .join(OrganizationUnit, OrganizationUnit.id == UserOrganizationAssignment.organization_unit_id)
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            Role.is_active.is_(True),
            UserOrganizationAssignment.is_active.is_(True),
            UserOrganizationAssignment.is_primary.is_(True),
            OrganizationUnit.is_active.is_(True),
        )
    )
    row = (await session.execute(statement)).one_or_none()
    if row is None:
        return None
    return UserAccessRecord(
        user=row[0],
        role_code=row[1],
        organization_unit_id=row[2],
        organization_code=row[3],
        organization_name=row[4],
        office_type=row[5].value,
    )

