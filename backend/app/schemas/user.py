from app.schemas.common import CamelModel


class UserOut(CamelModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool


class CreateUserIn(CamelModel):
    name: str
    email: str
    password: str
    role: str


class SetActiveIn(CamelModel):
    is_active: bool
