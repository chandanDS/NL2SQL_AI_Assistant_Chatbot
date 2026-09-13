from pydantic import BaseModel


class ScopedOrganizationResponse(BaseModel):
    id: int
    code: str
    name: str
    office_type: str
    parent_id: int | None
    depth: int


class OrganizationScopeResponse(BaseModel):
    role: str
    assigned_root_id: int
    effective_root_id: int
    organization_count: int
    organizations: list[ScopedOrganizationResponse]

