from enum import Enum
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
import json

class CardRegion(str, Enum):
    tashkent = "Toshkent"
    andijan = "Andijon"
    bukhara = "Buxoro"
    fergana = "Fargona"
    jizzakh = "Jizzax"
    namangan = "Namangan"
    navoiy = "Navoiy"
    qashkadaryo = "Qashqadaryo"
    samarkand = "Samarqand"
    sirdaryo = "Sirdaryo"
    surkhondaryo = "Surxondaryo"
    xorazm = "Xorazm"
    karakalpakstan = "Qoraqalpogiston"

class Card(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    description: str
    price: float
    discount_price: Optional[float] = Field(default=None, nullable=True)
    category_id: int = Field(foreign_key="category.id")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    image_urls_json: str = Field(default="[]", nullable=True)
    rating: float = Field(default=0.0)
    rating_count: int = Field(default=0)
    like_count: int = Field(default=0)
    view_count: int = Field(default=0)
    location_lat: float
    location_long: float
    region: CardRegion = Field(default=CardRegion.samarkand)
    phone_numbers_json: str = Field(default="[]", nullable=True)
    social_media_json: str = Field(default="{}", nullable=True)
    is_featured: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    
    @property
    def image_urls(self) -> List[str]:
        """Return the list of image URLs."""
        return json.loads(self.image_urls_json or "[]")

    @image_urls.setter
    def image_urls(self, values: List[str]):
        """Set the image URLs from a list."""
        self.image_urls_json = json.dumps(values)

    @property
    def phone_numbers(self) -> List[str]:
        """Return the list of phone numbers."""
        return json.loads(self.phone_numbers_json or "[]")

    @phone_numbers.setter
    def phone_numbers(self, values: List[str]):
        """Set the phone numbers from a list."""
        self.phone_numbers_json = json.dumps(values)

    @property
    def social_media(self) -> dict:
        """Return the social media links as a dictionary."""
        return json.loads(self.social_media_json or "{}")

    @social_media.setter
    def social_media(self, values: dict):
        """Set the social media links from a dictionary."""
        self.social_media_json = json.dumps(values)