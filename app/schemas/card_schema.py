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
    location_lat: float
    location_long: float
    region: CardRegion
    social_media: dict = Field(default_factory=dict)
    phone_numbers: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "name": "Example Card",
                "description": "A great item for sale.",
                "price": 100.0,
                "discount_price": 80.0,
                "category_id": 1,
                "location_lat": 41.2995,
                "location_long": 69.2401,
                "region": "Samarqand",
                "social_media": {"instagram": "https://instagram.com/example", "telegram": "https://t.me/example"},
                "phone_numbers": ["+998900003322", "+998888888888"],
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
        location_lat: float = Form(...),
        location_long: float = Form(...),
        region: CardRegion = Form(...),
        social_media: str = Form("{}"),
        phone_numbers: str = Form(""),
    ):
        # Parse phone numbers from comma-separated string to list
        parsed_phone_numbers = []
        if phone_numbers and phone_numbers.strip():
            parsed_phone_numbers = [phone.strip() for phone in phone_numbers.split(',') if phone.strip()]
        
        return cls(
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            category_id=category_id,
            location_lat=location_lat,
            location_long=location_long,
            region=region,
            social_media=json.loads(social_media or "{}"),
            phone_numbers=parsed_phone_numbers,
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

    @classmethod
    def from_card(cls, card: "Card") -> "CardRead":
        """Create CardRead from Card instance with proper property handling"""
        return cls(
            id=card.id,
            name=card.name,
            description=card.description,
            price=card.price,
            discount_price=card.discount_price,
            category_id=card.category_id,
            user_id=card.user_id,
            image_urls=card.image_urls,
            rating=card.rating,
            rating_count=card.rating_count,
            like_count=card.like_count,
            view_count=card.view_count,
            location_lat=card.location_lat,
            location_long=card.location_long,
            region=card.region,
            phone_numbers=card.phone_numbers,
            social_media=card.social_media,
            is_featured=card.is_featured,
            created_at=card.created_at,
            updated_at=card.updated_at,
        )


class CardUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    category_id: Optional[int] = None
    location_lat: Optional[float] = None
    location_long: Optional[float] = None
    region: Optional[CardRegion] = None
    social_media: Optional[str] = None
    phone_numbers: Optional[List[str]] = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def as_form(cls,
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
        price: Optional[float] = Form(None),
        discount_price: Optional[float] = Form(None),
        category_id: Optional[int] = Form(None),
        location_lat: Optional[float] = Form(None),
        location_long: Optional[float] = Form(None),
        region: Optional[CardRegion] = Form(None),
        social_media: Optional[str] = Form(None),
        phone_numbers: Optional[str] = Form(None),
    ):
        parsed_social_media = json.loads(social_media) if social_media else None
        
        # Parse phone numbers from comma-separated string to list
        parsed_phone_numbers = None
        if phone_numbers and phone_numbers.strip():
            parsed_phone_numbers = [phone.strip() for phone in phone_numbers.split(',') if phone.strip()]

        return cls(
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            category_id=category_id,
            location_lat=location_lat,
            location_long=location_long,
            region=region,
            social_media=parsed_social_media,
            phone_numbers=parsed_phone_numbers,
        )


class CardListResponse(SQLModel):
    total: int
    cards: list[CardRead]
    page: int
    size: int

    class Config:
        arbitrary_types_allowed = True
        