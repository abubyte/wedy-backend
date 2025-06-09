from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    admin = "admin"
    client = "client"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    firstname: str
    lastname: str
    login: str = Field(index=True, unique=True)
    hashed_password: str
    image_url: Optional[str] = Field(default=None, nullable=True)
    role: UserRole = Field(default=UserRole.client)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    verification_code: Optional[str] = Field(default=None, nullable=True)
    verification_code_expires: Optional[datetime] = Field(default=None, nullable=True)
    last_login: Optional[datetime] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    def update_password(self, new_password: str) -> None:
        self.hashed_password = self.get_password_hash(new_password)
        self.updated_at = datetime.utcnow()
        
    