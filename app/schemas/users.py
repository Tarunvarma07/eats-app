from enum import Enum
from datetime import datetime

from pydantic import BaseModel, EmailStr


class Department(str, Enum):
    HR = "HR"
    IT = "IT"
    FINANCE = "FINANCE"
    OPERATIONS = "OPERATIONS"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    department: Department


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    department: Department
    is_active: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
class AdminUserResponse(BaseModel):

    id: int

    name: str

    email: EmailStr

    role: str

    department: str | None

    is_active: bool

    is_approved: bool

    created_at: datetime

    model_config = {
        "from_attributes": True
    }