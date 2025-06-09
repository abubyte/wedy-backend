from typing import Optional, List
from pydantic import Field
from sqlmodel import SQLModel
import json
from datetime import datetime
from fastapi import Form

from app.models import Card
from app.models.card_model import CardRegion


class CardCreate(SQLModel):
    name: str = Field(index=True)
    description: str
    price: float
    discount_price: Optional[float] = None
    category_id: int
    user_id: Optional[int] = None
    location_lat: float
    location_long: float
    region: CardRegion
    phone_numbers: List[str] = Field(default_factory=list)
    social_media: dict = Field(default_factory=dict)
    is_featured: bool = False

    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "name": "Example Card",
                "description": "A great item for sale.",
                "price": 100.0,
                "discount_price": 80.0,
                "category_id": 1,
                "user_id": 1, # Example user_id
                "location_lat": 41.2995,
                "location_long": 69.2401,
                "region": "Samarqand",
                "phone_numbers": ["+998901234567"],
                "social_media": {"instagram": "https://instagram.com/example", "telegram": "https://t.me/example"},
                "is_featured": True
            }
        }

    @classmethod
    def as_form(cls,
        name: str = Form(...),
        description: str = Form(...),
        price: float = Form(...),
        discount_price: Optional[float] = Form(None),
        category_id: int = Form(...),
        user_id: Optional[int] = Form(None),
        location_lat: float = Form(...),
        location_long: float = Form(...),
        region: CardRegion = Form(...),
        phone_numbers: str = Form("[]"),
        social_media: str = Form("{}"),
        is_featured: bool = Form(False)
    ):
        return cls(
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            category_id=category_id,
            user_id=user_id,
            location_lat=location_lat,
            location_long=location_long,
            region=region,
            phone_numbers=json.loads(phone_numbers),
            social_media=json.loads(social_media),
            is_featured=is_featured
        )


class CardRead(SQLModel):
    id: int
    name: str
    description: str
    price: float
    discount_price: Optional[float] = None
    category_id: int
    user_id: Optional[int] = None
    image_urls: List[str]
    rating: float
    rating_count: int
    like_count: int
    view_count: int
    location_lat: float
    location_long: float
    region: CardRegion
    phone_numbers: List[str]
    social_media: dict
    is_featured: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        arbitrary_types_allowed = True
        from_attributes = True


class CardUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    category_id: Optional[int] = None
    user_id: Optional[int] = None
    location_lat: Optional[float] = None
    location_long: Optional[float] = None
    region: Optional[CardRegion] = None
    phone_numbers: Optional[List[str]] = None
    social_media: Optional[dict] = None
    is_featured: Optional[bool] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def as_form(cls,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        discount_price: Optional[float] = Form(None),
        category_id: Optional[int] = Form(None),
        user_id: Optional[int] = Form(None),
        location_lat: Optional[float] = Form(None),
        location_long: Optional[float] = Form(None),
        region: Optional[CardRegion] = Form(None),
        phone_numbers: Optional[str] = Form(None),
        social_media: Optional[str] = Form(None),
        is_featured: Optional[bool] = Form(None)
    ):
        parsed_phone_numbers = json.loads(phone_numbers) if phone_numbers else None
        parsed_social_media = json.loads(social_media) if social_media else None

        return cls(
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            category_id=category_id,
            user_id=user_id,
            location_lat=location_lat,
            location_long=location_long,
            region=region,
            phone_numbers=parsed_phone_numbers,
            social_media=parsed_social_media,
            is_featured=is_featured
        )


class CardListResponse(SQLModel):
    total: int
    cards: list[CardRead]
    page: int
    size: int

    class Config:
        arbitrary_types_allowed = True 