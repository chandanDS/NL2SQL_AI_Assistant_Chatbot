import asyncio
from dataclasses import dataclass

from faker import Faker
from pwdlib import PasswordHash
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.db.session import get_session_factory
from backend.models.identity import Role, User, UserOrganizationAssignment, UserRole
from backend.models.organization import OfficeType, OrganizationHierarchy, OrganizationUnit


@dataclass(frozen=True)
class Location:
    city: str
    state: str


CIRCLES: tuple[tuple[str, str, tuple[Location, ...]], ...] = (
    ("NORTH", "North Circle", (Location("New Delhi", "Delhi"), Location("Chandigarh", "Chandigarh"), Location("Dehradun", "Uttarakhand"), Location("Shimla", "Himachal Pradesh"))),
    ("WEST", "West Circle", (Location("Mumbai", "Maharashtra"), Location("Pune", "Maharashtra"), Location("Ahmedabad", "Gujarat"), Location("Panaji", "Goa"))),
    ("SOUTH", "South Circle", (Location("Chennai", "Tamil Nadu"), Location("Bengaluru", "Karnataka"), Location("Hyderabad", "Telangana"), Location("Kochi", "Kerala"))),
    ("EAST", "East Circle", (Location("Kolkata", "West Bengal"), Location("Bhubaneswar", "Odisha"), Location("Patna", "Bihar"), Location("Ranchi", "Jharkhand"))),
    ("CENTRAL", "Central Circle", (Location("Bhopal", "Madhya Pradesh"), Location("Indore", "Madhya Pradesh"), Location("Raipur", "Chhattisgarh"), Location("Nagpur", "Maharashtra"))),
    ("NORTHEAST", "North East Circle", (Location("Guwahati", "Assam"), Location("Shillong", "Meghalaya"), Location("Imphal", "Manipur"), Location("Agartala", "Tripura"))),
    ("UP", "Uttar Pradesh Circle", (Location("Lucknow", "Uttar Pradesh"), Location("Kanpur", "Uttar Pradesh"), Location("Varanasi", "Uttar Pradesh"), Location("Prayagraj", "Uttar Pradesh"))),
    ("RAJ", "Rajasthan Circle", (Location("Jaipur", "Rajasthan"), Location("Jodhpur", "Rajasthan"), Location("Udaipur", "Rajasthan"), Location("Kota", "Rajasthan"))),
)

ROLE_DEFINITIONS = (
    ("HO_USER", "Head office user", "Access scope starts at Head Office.", 0),
    ("CO_USER", "Circle office user", "Access scope starts at the assigned Circle Office.", 1),
    ("RO_USER", "Regional office user", "Access scope starts at the assigned Regional Office.", 2),
    ("BRANCH_USER", "Branch user", "Access scope is limited to the assigned Branch.", 3),
)

PASSWORD_HASHER = PasswordHash.recommended()


async def add_unit(
    session: AsyncSession,
    ancestors: dict[int, list[tuple[int, int]]],
    *,
    code: str,
    name: str,
    office_type: OfficeType,
    parent: OrganizationUnit | None,
    state: str | None = None,
    city: str | None = None,
) -> OrganizationUnit:
    unit = OrganizationUnit(
        code=code,
        name=name,
        office_type=office_type,
        parent_id=parent.id if parent else None,
        state=state,
        district=city,
        city=city,
    )
    session.add(unit)
    await session.flush()

    paths = [(unit.id, 0)]
    if parent:
        paths.extend((ancestor_id, depth + 1) for ancestor_id, depth in ancestors[parent.id])
    ancestors[unit.id] = paths
    session.add_all(
        OrganizationHierarchy(
            ancestor_id=ancestor_id,
            descendant_id=unit.id,
            depth=depth,
        )
        for ancestor_id, depth in paths
    )
    return unit


async def create_organization(session: AsyncSession) -> dict[OfficeType, list[OrganizationUnit]]:
    units: dict[OfficeType, list[OrganizationUnit]] = {office_type: [] for office_type in OfficeType}
    ancestors: dict[int, list[tuple[int, int]]] = {}

    ho = await add_unit(
        session,
        ancestors,
        code="HO001",
        name="National Head Office",
        office_type=OfficeType.HO,
        parent=None,
        state="Delhi",
        city="New Delhi",
    )
    units[OfficeType.HO].append(ho)

    ro_number = 0
    branch_number = 0
    for circle_number, (circle_code, circle_name, locations) in enumerate(CIRCLES, start=1):
        co = await add_unit(
            session,
            ancestors,
            code=f"CO{circle_number:03d}",
            name=circle_name,
            office_type=OfficeType.CO,
            parent=ho,
        )
        units[OfficeType.CO].append(co)

        for location in locations:
            ro_number += 1
            ro = await add_unit(
                session,
                ancestors,
                code=f"RO{ro_number:03d}",
                name=f"{location.city} Regional Office",
                office_type=OfficeType.RO,
                parent=co,
                state=location.state,
                city=location.city,
            )
            units[OfficeType.RO].append(ro)

            for local_branch_number in range(1, 9):
                branch_number += 1
                branch = await add_unit(
                    session,
                    ancestors,
                    code=f"BR{branch_number:04d}",
                    name=f"{location.city} Branch {local_branch_number:02d}",
                    office_type=OfficeType.BRANCH,
                    parent=ro,
                    state=location.state,
                    city=location.city,
                )
                units[OfficeType.BRANCH].append(branch)

    return units


async def create_roles(session: AsyncSession) -> dict[str, Role]:
    roles = {
        code: Role(
            code=code,
            name=name,
            description=description,
            hierarchy_level=hierarchy_level,
        )
        for code, name, description, hierarchy_level in ROLE_DEFINITIONS
    }
    session.add_all(roles.values())
    await session.flush()
    return roles


async def create_users(
    session: AsyncSession,
    roles: dict[str, Role],
    units: dict[OfficeType, list[OrganizationUnit]],
    password: str,
) -> None:
    fake = Faker("en_IN")
    Faker.seed(20260913)
    user_number = 0

    assignments: list[tuple[str, OrganizationUnit]] = []
    assignments.extend(("HO_USER", units[OfficeType.HO][0]) for _ in range(8))
    for unit in units[OfficeType.CO]:
        assignments.extend(("CO_USER", unit) for _ in range(4))
    for unit in units[OfficeType.RO]:
        assignments.extend(("RO_USER", unit) for _ in range(3))
    assignments.extend(("BRANCH_USER", unit) for unit in units[OfficeType.BRANCH])
    assignments.extend(("BRANCH_USER", unit) for unit in units[OfficeType.BRANCH][:8])

    if len(assignments) != 400:
        raise RuntimeError(f"Expected 400 assignments, generated {len(assignments)}")

    for role_code, organization_unit in assignments:
        user_number += 1
        username = f"bankuser{user_number:04d}"
        user = User(
            employee_id=f"BNK{user_number:06d}",
            username=username,
            email=f"{username}@example.com",
            full_name=fake.name(),
            password_hash=PASSWORD_HASHER.hash(password),
        )
        session.add(user)
        await session.flush()
        session.add(UserRole(user_id=user.id, role_id=roles[role_code].id))
        session.add(
            UserOrganizationAssignment(
                user_id=user.id,
                organization_unit_id=organization_unit.id,
                is_primary=True,
                is_active=True,
            )
        )


async def seed() -> None:
    settings = get_settings()
    password = settings.synthetic_user_password.get_secret_value()
    if len(password) < 16:
        raise RuntimeError("SYNTHETIC_USER_PASSWORD must contain at least 16 characters")

    session_factory = get_session_factory()
    async with session_factory() as session, session.begin():
        existing_users = await session.scalar(select(func.count()).select_from(User))
        existing_units = await session.scalar(select(func.count()).select_from(OrganizationUnit))
        existing_roles = await session.scalar(select(func.count()).select_from(Role))

        if existing_users == 400 and existing_units == 297 and existing_roles == 4:
            print("Synthetic identity data already exists; no changes made.")
            return
        if existing_users or existing_units or existing_roles:
            raise RuntimeError(
                "Identity seed requires empty organization, role and user tables; "
                f"found users={existing_users}, units={existing_units}, roles={existing_roles}"
            )

        units = await create_organization(session)
        roles = await create_roles(session)
        await create_users(session, roles, units, password)

    print("Created 297 organization units, 4 roles and 400 synthetic users.")


if __name__ == "__main__":
    asyncio.run(seed())

