from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

# class TariffLimits:
#     photos_limit

class Tariff(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    price: float = Field(ge=0)
    duration_days: int = Field(gt=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id")
    
    search_priority: int = Field(default=0, ge=0)
    has_website: bool = Field(default=False)
    max_social_medias: int = Field(default=0, ge=0)
    max_description_chars: int = Field(default=0, ge=0)
    max_phone_numbers: int = Field(default=0, ge=0)
    max_images: int = Field(default=0, ge=0)
    