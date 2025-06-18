from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from fastapi import Form

class TariffBase(BaseModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    price: float = Field(ge=0)
    duration_days: int = Field(gt=0)
    is_active: bool = True
    search_priority: int = Field(default=0, ge=0)
    has_website: bool = Field(default=False)
    max_social_medias: int = Field(default=0, ge=0)
    max_description_chars: int = Field(default=0, ge=0)
    max_phone_numbers: int = Field(default=0, ge=0)
    max_images: int = Field(default=0, ge=0)

    @classmethod
    def as_form(
        cls,
        name: str = Form(...),
        description: Optional[str] = Form(None),
        price: float = Form(...),
        duration_days: int = Form(...),
        is_active: bool = Form(True),
        search_priority: int = Form(0),
        has_website: bool = Form(False),
        max_social_medias: int = Form(0),
        max_description_chars: int = Form(0),
        max_phone_numbers: int = Form(0),
        max_images: int = Form(0)
    ):
        return cls(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            is_active=is_active,
            search_priority=search_priority,
            has_website=has_website,
            max_social_medias=max_social_medias,
            max_description_chars=max_description_chars,
            max_phone_numbers=max_phone_numbers,
            max_images=max_images
        )

class TariffCreate(TariffBase):
    pass

class TariffUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    duration_days: Optional[int] = Field(default=None, gt=0)
    is_active: Optional[bool] = None
    search_priority: Optional[int] = Field(default=None, ge=0)
    has_website: Optional[bool] = None
    max_social_medias: Optional[int] = Field(default=None, ge=0)
    max_description_chars: Optional[int] = Field(default=None, ge=0)
    max_phone_numbers: Optional[int] = Field(default=None, ge=0)
    max_images: Optional[int] = Field(default=None, ge=0)

    @classmethod
    def as_form(
        cls,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        duration_days: Optional[int] = Form(None),
        is_active: Optional[bool] = Form(None),
        search_priority: Optional[int] = Form(None),
        has_website: Optional[bool] = Form(None),
        max_social_medias: Optional[int] = Form(None),
        max_description_chars: Optional[int] = Form(None),
        max_phone_numbers: Optional[int] = Form(None),
        max_images: Optional[int] = Form(None)
    ):
        return cls(
            name=name,
            description=description,
            price=price,
            duration_days=duration_days,
            is_active=is_active,
            search_priority=search_priority,
            has_website=has_website,
            max_social_medias=max_social_medias,
            max_description_chars=max_description_chars,
            max_phone_numbers=max_phone_numbers,
            max_images=max_images
        )

class TariffRead(TariffBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True

class TariffResponse(BaseModel):
    message: str
    tariff: TariffRead

class TariffListResponse(BaseModel):
    total: int
    tariffs: List[TariffRead]
    page: int
    size: int 