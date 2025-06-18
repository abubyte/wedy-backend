from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from passlib.context import CryptContext
from app.models.tariff_model import Tariff

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRole(str, Enum):
    admin = "admin"
    client = "client"

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    firstname: str = Field(max_length=50)
    lastname: str = Field(max_length=50)
    login: str = Field(unique=True, index=True)
    hashed_password: str
    image_url: Optional[str] = None
    role: UserRole = Field(default=UserRole.client)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    verification_code: Optional[str] = None
    verification_code_expires: Optional[datetime] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    tariff_id: Optional[int] = Field(default=None, foreign_key="tariff.id")
    tariff_expires_at: Optional[datetime] = None

    def verify_password(self, plain_password: str) -> bool:
        return pwd_context.verify(plain_password, self.hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    def update_password(self, new_password: str) -> None:
        self.hashed_password = self.get_password_hash(new_password)
        self.updated_at = datetime.utcnow()
        
    