from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    must_change_password: bool


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: str
    username: str
    email: str
    full_name: str
    role: str
    organization_unit_id: int
    organization_code: str
    organization_name: str
    office_type: str
    must_change_password: bool

