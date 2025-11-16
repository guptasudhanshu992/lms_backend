from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import datetime
from ..core.database import get_db
from ..core.security import get_current_user, get_current_admin_user
from ..models import User, Coupon, Cart
from ..schemas.coupon import (
    CouponCreate,
    CouponUpdate,
    CouponResponse,
    ApplyCouponRequest,
    ApplyCouponResponse,
)

router = APIRouter(tags=["coupons"])


# ==================== ADMIN COUPON MANAGEMENT ====================

@router.post("/admin/coupons", response_model=CouponResponse)
async def create_coupon(
    coupon: CouponCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Create a new coupon (Admin only)."""
    # Check if coupon code already exists
    existing = db.query(Coupon).filter(Coupon.code == coupon.code.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Coupon code already exists")
    
    db_coupon = Coupon(
        code=coupon.code.upper(),
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        min_purchase_amount=coupon.min_purchase_amount,
        max_discount_amount=coupon.max_discount_amount,
        usage_limit=coupon.usage_limit,
        is_active=coupon.is_active,
        valid_from=coupon.valid_from or datetime.utcnow(),
        valid_until=coupon.valid_until,
        creator_id=current_user.id,
    )
    db.add(db_coupon)
    db.commit()
    db.refresh(db_coupon)
    return db_coupon


@router.get("/admin/coupons", response_model=List[CouponResponse])
async def get_all_coupons(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get all coupons (Admin only)."""
    coupons = db.query(Coupon).order_by(Coupon.created_at.desc()).all()
    return coupons


@router.get("/admin/coupons/{coupon_id}", response_model=CouponResponse)
async def get_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get coupon by ID (Admin only)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    return coupon


@router.put("/admin/coupons/{coupon_id}", response_model=CouponResponse)
async def update_coupon(
    coupon_id: int,
    coupon_update: CouponUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Update coupon (Admin only)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    update_data = coupon_update.model_dump(exclude_unset=True)
    
    # Check if code is being changed and if it's unique
    if 'code' in update_data:
        new_code = update_data['code'].upper()
        existing = db.query(Coupon).filter(
            Coupon.code == new_code,
            Coupon.id != coupon_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Coupon code already exists")
        update_data['code'] = new_code
    
    for field, value in update_data.items():
        setattr(coupon, field, value)
    
    coupon.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(coupon)
    return coupon


@router.delete("/admin/coupons/{coupon_id}")
async def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Any:
    """Delete coupon (Admin only)."""
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")
    
    db.delete(coupon)
    db.commit()
    return {"message": "Coupon deleted successfully"}


# ==================== USER COUPON VALIDATION ====================

@router.post("/cart/apply-coupon", response_model=ApplyCouponResponse)
async def apply_coupon_to_cart(
    request: ApplyCouponRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Validate and apply coupon to cart."""
    # Get coupon
    coupon = db.query(Coupon).filter(
        Coupon.code == request.coupon_code.upper()
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon code")
    
    # Validate coupon
    now = datetime.utcnow()
    
    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="This coupon is no longer active")
    
    if coupon.valid_until and coupon.valid_until < now:
        raise HTTPException(status_code=400, detail="This coupon has expired")
    
    if coupon.valid_from and coupon.valid_from > now:
        raise HTTPException(status_code=400, detail="This coupon is not yet valid")
    
    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="This coupon has reached its usage limit")
    
    # Get cart items
    from sqlalchemy.orm import joinedload
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).options(joinedload(Cart.course)).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty")
    
    # Calculate original total
    original_total = sum(item.course.price for item in cart_items)
    
    # Check minimum purchase amount
    if coupon.min_purchase_amount and original_total < coupon.min_purchase_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum purchase amount of ${coupon.min_purchase_amount} required"
        )
    
    # Calculate discount
    if coupon.discount_type == "percentage":
        discount_amount = original_total * (coupon.discount_value / 100)
        # Apply max discount cap if set
        if coupon.max_discount_amount:
            discount_amount = min(discount_amount, coupon.max_discount_amount)
    else:  # fixed
        discount_amount = min(coupon.discount_value, original_total)
    
    final_total = max(0, original_total - discount_amount)
    
    return ApplyCouponResponse(
        coupon_code=coupon.code,
        discount_amount=round(discount_amount, 2),
        original_total=round(original_total, 2),
        final_total=round(final_total, 2),
        message=f"Coupon applied successfully! You saved ${round(discount_amount, 2)}"
    )


@router.post("/cart/validate-coupon")
async def validate_coupon(
    request: ApplyCouponRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Quick validation without calculating discount."""
    coupon = db.query(Coupon).filter(
        Coupon.code == request.coupon_code.upper()
    ).first()
    
    if not coupon:
        raise HTTPException(status_code=404, detail="Invalid coupon code")
    
    now = datetime.utcnow()
    
    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="This coupon is no longer active")
    
    if coupon.valid_until and coupon.valid_until < now:
        raise HTTPException(status_code=400, detail="This coupon has expired")
    
    return {"message": "Coupon is valid", "code": coupon.code}
