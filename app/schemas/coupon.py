from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
from enum import Enum


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class CouponBase(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: float
    min_purchase_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @field_validator('code')
    @classmethod
    def validate_code(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Coupon code must be at least 3 characters')
        return v.upper().strip()

    @field_validator('discount_value')
    @classmethod
    def validate_discount(cls, v, info):
        if v <= 0:
            raise ValueError('Discount value must be positive')
        if info.data.get('discount_type') == DiscountType.PERCENTAGE and v > 100:
            raise ValueError('Percentage discount cannot exceed 100%')
        return v


class CouponCreate(CouponBase):
    pass


class CouponUpdate(BaseModel):
    code: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    min_purchase_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = None
    valid_until: Optional[datetime] = None


class CouponResponse(BaseModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_value: float
    min_purchase_amount: Optional[float]
    max_discount_amount: Optional[float]
    usage_limit: Optional[int]
    usage_count: int
    is_active: bool
    valid_from: datetime
    valid_until: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ApplyCouponRequest(BaseModel):
    coupon_code: str


class ApplyCouponResponse(BaseModel):
    coupon_code: str
    discount_amount: float
    original_total: float
    final_total: float
    message: str
