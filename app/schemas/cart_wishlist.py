from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WishlistItemBase(BaseModel):
    course_id: int


class WishlistItemCreate(WishlistItemBase):
    pass


class WishlistItemResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class CartItemBase(BaseModel):
    course_id: int


class CartItemCreate(CartItemBase):
    pass


class CartItemResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
