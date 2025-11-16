from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentBase(BaseModel):
    course_id: int
    amount: float = Field(..., gt=0)
    currency: str = "USD"


class PaymentCreate(PaymentBase):
    pass


class CheckoutSessionRequest(BaseModel):
    course_id: int
    success_url: str
    cancel_url: str


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    amount: float
    currency: str
    status: str
    payment_method: Optional[str] = None
    transaction_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PaymentStatsResponse(BaseModel):
    total_revenue: float
    total_transactions: int
    successful_payments: int
    pending_payments: int
    failed_payments: int


class WebhookEvent(BaseModel):
    type: str
    data: dict
