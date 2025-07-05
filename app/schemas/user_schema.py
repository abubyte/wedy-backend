from pydantic import BaseModel, EmailStr, validator
from typing import Annotated, Optional, List
from pydantic import StringConstraints
from datetime import datetime
from app.models.user_model import UserRole
from fastapi import Form
import re
from app.schemas.tariff_schema import TariffRead

# Phone number validation regex
PHONE_REGEX = r'^\+998\d{9}$'
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
LOGIN_REGEX = r'^(?:\+998\d{9}|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})$'


class UserVerifyRequest(BaseModel):
    login: Annotated[str, StringConstraints(pattern=LOGIN_REGEX)]
    code: Annotated[str, StringConstraints(min_length=4, max_length=6)]
    
    @classmethod
    def as_form(
        cls,
        login: str = Form(...),
        code: str = Form(...),
    ):
        return cls(login=login, code=code)

class UserBase(BaseModel):
    firstname: str
    lastname: str
    login: str

class UserCreate(UserBase):
    password: str

    @validator('login')
    def validate_login(cls, v):
        if not re.match(LOGIN_REGEX, v):
            raise ValueError('Login can only be email or Uzbekistan phone number')
        return v

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

    @classmethod
    def as_form(
        cls,
        firstname: str = Form(...),
        lastname: str = Form(...),
        login: str = Form(...),
        password: str = Form(...),
    ):
        return cls(
            firstname=firstname,
            lastname=lastname,
            login=login,
            password=password,
        )

class UserRead(UserBase):
    id: int
    role: UserRole
    is_verified: bool
    image_url: Optional[str]
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    tariff_id: Optional[int] = None
    tariff_expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    firstname: Optional[str] = None
    lastname: Optional[str] = None

    @classmethod
    def as_form(
        cls,
        firstname: str = Form(None),
        lastname: str = Form(None),
    ):
        return cls(
            firstname=firstname,
            lastname=lastname,
        )

class UserResponse(BaseModel):
    message: str
    user: UserRead

class UserListResponse(BaseModel):
    total: int
    users: list[UserRead]
    page: int
    size: int

class UserRoleUpdate(BaseModel):
    role: UserRole

    @classmethod
    def as_form(
        cls,
        role: UserRole = Form(...),
    ):
        return cls(role=role)

class UserLogin(BaseModel):
    login: Annotated[str, StringConstraints(pattern=LOGIN_REGEX)]
    password: Annotated[str, StringConstraints(min_length=8)]

    @validator('login')
    def validate_login(cls, v):
        if not re.match(LOGIN_REGEX, v):
            raise ValueError('Login can only be email or Uzbekistan phone number')
        return v

    @validator('password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

    @classmethod
    def as_form(
        cls,
        login: str = Form(...),
        password: str = Form(...),
    ):
        return cls(login=login, password=password)

class PasswordReset(BaseModel):
    login: Annotated[str, StringConstraints(pattern=LOGIN_REGEX)]
    new_password: Annotated[str, StringConstraints(min_length=8)]
    verification_code: Annotated[str, StringConstraints(min_length=4, max_length=6)]

    @validator('login')
    def validate_login(cls, v):
        if not re.match(LOGIN_REGEX, v):
            raise ValueError('Login can only be email or Uzbekistan phone number')
        return v

    @validator('new_password')
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one number')
        return v

    @classmethod
    def as_form(
        cls,
        login: str = Form(...),
        new_password: str = Form(...),
        verification_code: str = Form(...),
    ):
        return cls(
            login=login,
            new_password=new_password,
            verification_code=verification_code
        )