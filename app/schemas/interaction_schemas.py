from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# Review Schemas
class ReviewCreate(BaseModel):
    rating: float = Field(ge=1, le=5)
    comment: str

class ReviewUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1, le=5)
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    card_id: int
    user_id: int
    rating: float
    comment: str
    created_at: datetime
    updated_at: datetime
    user_firstname: str
    user_lastname: str

class ReviewListResponse(BaseModel):
    total: int
    reviews: List[ReviewResponse]
    page: int
    size: int

# Like Schemas
class LikeResponse(BaseModel):
    id: int
    card_id: int
    user_id: int
    created_at: datetime

# View Schemas
class ViewResponse(BaseModel):
    id: int
    card_id: int
    user_id: Optional[int]
    ip_address: Optional[str]
    created_at: datetime 