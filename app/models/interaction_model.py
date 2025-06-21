from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="card.id")
    user_id: int = Field(foreign_key="user.id")
    rating: float = Field(ge=1, le=5)  # Rating from 1 to 5
    comment: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Like(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="card.id")
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class View(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    card_id: int = Field(foreign_key="card.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)  # Optional for anonymous views
    ip_address: Optional[str] = Field(default=None, nullable=True)  # Store IP for anonymous views
    created_at: datetime = Field(default_factory=datetime.utcnow) 