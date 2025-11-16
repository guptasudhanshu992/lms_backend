from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, Optional
from datetime import datetime
import stripe

from ..core.database import get_db
from ..core.security import get_current_active_user, get_current_admin_user
from ..core.config import settings
from ..models.user import User
from ..models.course import Course
from ..models.payment import Payment
from ..models.enrollment import Enrollment
from ..schemas.payment import (
    CheckoutSessionRequest, CheckoutSessionResponse,
    PaymentResponse, PaymentStatsResponse
)

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request_data: CheckoutSessionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Create a Stripe checkout session for course purchase."""
    # Check if course exists
    course = db.query(Course).filter(Course.id == request_data.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )
    
    # Check if already enrolled
    existing_enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == current_user.id,
        Enrollment.course_id == request_data.course_id,
        Enrollment.is_active == True
    ).first()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already enrolled in this course"
        )
    
    try:
        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(course.price * 100),  # Convert to cents
                        'product_data': {
                            'name': course.title,
                            'description': course.description or '',
                            'images': [course.thumbnail_url] if course.thumbnail_url else [],
                        },
                    },
                    'quantity': 1,
                }
            ],
            mode='payment',
            success_url=request_data.success_url,
            cancel_url=request_data.cancel_url,
            client_reference_id=str(current_user.id),
            metadata={
                'user_id': str(current_user.id),
                'course_id': str(course.id),
                'user_email': current_user.email
            }
        )
        
        # Create pending payment record
        payment = Payment(
            user_id=current_user.id,
            course_id=course.id,
            amount=course.price,
            currency='USD',
            status='pending',
            stripe_session_id=checkout_session.id
        )
        
        db.add(payment)
        db.commit()
        
        return {
            "session_id": checkout_session.id,
            "checkout_url": checkout_session.url
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None),
    db: Session = Depends(get_db)
) -> Any:
    """Handle Stripe webhook events."""
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Get payment record
        payment = db.query(Payment).filter(
            Payment.stripe_session_id == session.id
        ).first()
        
        if payment:
            # Update payment status
            payment.status = 'completed'
            payment.stripe_payment_intent_id = session.payment_intent
            payment.completed_at = datetime.utcnow()
            
            # Create enrollment
            enrollment = Enrollment(
                user_id=payment.user_id,
                course_id=payment.course_id,
                is_active=True,
                progress=0.0
            )
            
            db.add(enrollment)
            db.commit()
    
    return {"status": "success"}


@router.get("/my-payments", response_model=list[PaymentResponse])
async def get_my_payments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get all payments made by current user."""
    payments = db.query(Payment).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()
    
    return payments


@router.get("/stats", response_model=PaymentStatsResponse)
async def get_payment_stats(
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get payment statistics (Admin only)."""
    # Total revenue
    total_revenue = db.query(func.sum(Payment.amount)).filter(
        Payment.status == 'completed'
    ).scalar() or 0.0
    
    # Total transactions
    total_transactions = db.query(Payment).count()
    
    # Payment status counts
    successful_payments = db.query(Payment).filter(Payment.status == 'completed').count()
    pending_payments = db.query(Payment).filter(Payment.status == 'pending').count()
    failed_payments = db.query(Payment).filter(Payment.status == 'failed').count()
    
    return {
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "successful_payments": successful_payments,
        "pending_payments": pending_payments,
        "failed_payments": failed_payments
    }


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment_by_id(
    payment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """Get payment details by ID."""
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Users can only view their own payments, admins can view all
    if current_user.role != "admin" and payment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this payment"
        )
    
    return payment
