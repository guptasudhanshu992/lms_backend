from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..core.database import Base


class DiscountType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED = "fixed"


class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_type = Column(Enum(DiscountType), nullable=False)
    discount_value = Column(Float, nullable=False)  # percentage (0-100) or fixed amount
    min_purchase_amount = Column(Float, nullable=True)  # Minimum cart value required
    max_discount_amount = Column(Float, nullable=True)  # Max discount for percentage type
    usage_limit = Column(Integer, nullable=True)  # Total times coupon can be used
    usage_count = Column(Integer, default=0)  # Times coupon has been used
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, default=datetime.utcnow)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator_id = Column(Integer, nullable=True)  # Admin who created it
