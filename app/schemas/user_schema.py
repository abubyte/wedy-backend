from pydantic import BaseModel, EmailStr, validator
from typing import Annotated, Optional, List
from pydantic import StringConstraints
from datetime import datetime
from app.models.user_model import UserRole
from fastapi import Form
import re

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

class UserCreate(BaseModel):
    firstname: Annotated[str, StringConstraints(min_length=2, max_length=50)]
    lastname: Annotated[str, StringConstraints(min_length=2, max_length=50)]
    login: Annotated[str, StringConstraints(min_length=3, max_length=50)]
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

class UserRead(BaseModel):
    id: int
    firstname: str
    lastname: str
    login: str
    role: UserRole
    is_verified: bool
    image_url: Optional[str]  
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    firstname: str = Form(...)
    lastname: str = Form(...)

    @classmethod
    def as_form(
        cls,
        firstname: str = Form(...),
        lastname: str = Form(...),
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