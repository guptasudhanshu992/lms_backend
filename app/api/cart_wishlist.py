from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Any
from ..core.database import get_db
from ..core.security import get_current_user
from ..models import User, Wishlist, Cart, Course, Enrollment, Coupon
from ..schemas.cart_wishlist import (
    WishlistItemCreate,
    WishlistItemResponse,
    CartItemCreate,
    CartItemResponse,
)
from ..schemas.course import CourseResponse

router = APIRouter(tags=["cart-wishlist"])


# ==================== WISHLIST ENDPOINTS ====================

@router.post("/wishlist", response_model=WishlistItemResponse)
async def add_to_wishlist(
    item: WishlistItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Add a course to user's wishlist."""
    # Check if course exists
    course = db.query(Course).filter(Course.id == item.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is already enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == item.course_id
    ).first()
    if enrollment:
        raise HTTPException(status_code=400, detail="You are already enrolled in this course")
    
    # Check if already in wishlist
    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.course_id == item.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course already in wishlist")
    
    # Add to wishlist
    wishlist_item = Wishlist(
        user_id=current_user.id,
        course_id=item.course_id
    )
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    return wishlist_item


@router.get("/wishlist", response_model=List[CourseResponse])
async def get_wishlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get user's wishlist with course details."""
    wishlist_items = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id
    ).options(joinedload(Wishlist.course)).all()
    
    return [item.course for item in wishlist_items]


@router.delete("/wishlist/{course_id}")
async def remove_from_wishlist(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Remove a course from user's wishlist."""
    wishlist_item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.course_id == course_id
    ).first()
    
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Course not found in wishlist")
    
    db.delete(wishlist_item)
    db.commit()
    return {"message": "Course removed from wishlist"}


@router.post("/wishlist/{course_id}/move-to-cart")
async def move_to_cart(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Move a course from wishlist to cart."""
    # Check if in wishlist
    wishlist_item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.course_id == course_id
    ).first()
    
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Course not found in wishlist")
    
    # Check if already in cart
    existing_cart = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.course_id == course_id
    ).first()
    
    if not existing_cart:
        # Add to cart
        cart_item = Cart(
            user_id=current_user.id,
            course_id=course_id
        )
        db.add(cart_item)
    
    # Remove from wishlist
    db.delete(wishlist_item)
    db.commit()
    
    return {"message": "Course moved to cart"}


# ==================== CART ENDPOINTS ====================

@router.post("/cart", response_model=CartItemResponse)
async def add_to_cart(
    item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Add a course to user's cart."""
    # Check if course exists
    course = db.query(Course).filter(Course.id == item.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Check if user is already enrolled
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == item.course_id
    ).first()
    if enrollment:
        raise HTTPException(status_code=400, detail="You are already enrolled in this course")
    
    # Check if already in cart
    existing = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.course_id == item.course_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Course already in cart")
    
    # Add to cart
    cart_item = Cart(
        user_id=current_user.id,
        course_id=item.course_id
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)
    return cart_item


@router.get("/cart", response_model=List[CourseResponse])
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get user's cart with course details."""
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).options(joinedload(Cart.course)).all()
    
    return [item.course for item in cart_items]


@router.delete("/cart/{course_id}")
async def remove_from_cart(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Remove a course from user's cart."""
    cart_item = db.query(Cart).filter(
        Cart.user_id == current_user.id,
        Cart.course_id == course_id
    ).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Course not found in cart")
    
    db.delete(cart_item)
    db.commit()
    return {"message": "Course removed from cart"}


@router.post("/cart/checkout")
async def checkout(
    coupon_code: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Checkout all items in cart (create enrollments)."""
    from datetime import datetime
    
    # Get all cart items
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).options(joinedload(Cart.course)).all()
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total
    total_price = sum(item.course.price for item in cart_items)
    discount_amount = 0
    final_price = total_price
    
    # Apply coupon if provided
    if coupon_code:
        coupon = db.query(Coupon).filter(Coupon.code == coupon_code.upper()).first()
        if coupon and coupon.is_active:
            now = datetime.utcnow()
            if (not coupon.valid_until or coupon.valid_until >= now) and \
               (not coupon.usage_limit or coupon.usage_count < coupon.usage_limit):
                # Calculate discount
                if coupon.discount_type == "percentage":
                    discount_amount = total_price * (coupon.discount_value / 100)
                    if coupon.max_discount_amount:
                        discount_amount = min(discount_amount, coupon.max_discount_amount)
                else:  # fixed
                    discount_amount = min(coupon.discount_value, total_price)
                
                final_price = max(0, total_price - discount_amount)
                
                # Increment usage count
                coupon.usage_count += 1
    
    # Create enrollments for each course
    for cart_item in cart_items:
        # Check if not already enrolled
        existing_enrollment = db.query(Enrollment).filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id == cart_item.course_id
        ).first()
        
        if not existing_enrollment:
            enrollment = Enrollment(
                user_id=current_user.id,
                course_id=cart_item.course_id
            )
            db.add(enrollment)
        
        # Remove from cart
        db.delete(cart_item)
    
    db.commit()
    
    return {
        "message": "Checkout successful",
        "original_price": total_price,
        "discount_amount": discount_amount,
        "final_price": final_price,
        "courses_enrolled": len(cart_items)
    }


@router.get("/cart/total")
async def get_cart_total(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Any:
    """Get cart total price and item count."""
    cart_items = db.query(Cart).filter(
        Cart.user_id == current_user.id
    ).options(joinedload(Cart.course)).all()
    
    total_price = sum(item.course.price for item in cart_items)
    
    return {
        "total_price": total_price,
        "item_count": len(cart_items)
    }
