# app/api/endpoints/billing.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from app.api.models.user import User, PaymentHistory
from app.core.auth import get_current_user, get_admin_user
from app.db.database import get_db
from app.services.billing_service import BillingService
from typing import List, Optional
import uuid
from pydantic import BaseModel, UUID4, Field
import stripe
import os
import json
from datetime import datetime

router = APIRouter()

# Pydantic models for request/response validation
class PaymentMethodResponse(BaseModel):
    id: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool

class PaymentHistoryResponse(BaseModel):
    id: UUID4
    amount: float
    status: str
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class PaymentMethodRequest(BaseModel):
    payment_method_id: str

class InvoicePreviewRequest(BaseModel):
    plan_id: UUID4

class OneTimeChargeRequest(BaseModel):
    amount: float
    description: str


@router.post("/setup-intent")
async def create_setup_intent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe SetupIntent for securely collecting payment method details"""
    try:
        setup_intent = await BillingService.create_setup_intent(db, str(current_user.id))
        return setup_intent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all payment methods for the current user"""
    try:
        payment_methods = await BillingService.get_payment_methods(db, str(current_user.id))
        return payment_methods
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/payment-methods/default")
async def update_default_payment_method(
    payment_data: PaymentMethodRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the default payment method for the current user"""
    try:
        result = await BillingService.update_default_payment_method(
            db, 
            str(current_user.id), 
            payment_data.payment_method_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/payment-methods/{payment_method_id}")
async def remove_payment_method(
    payment_method_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a payment method for the current user"""
    try:
        result = await BillingService.remove_payment_method(
            db, 
            str(current_user.id), 
            payment_method_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/payment-history", response_model=List[PaymentHistoryResponse])
async def get_payment_history(
    limit: int = 10, 
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get payment history for the current user"""
    try:
        payments = await BillingService.get_payment_history(db, str(current_user.id), limit, offset)
        return payments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/invoice-preview")
async def get_subscription_invoice_preview(
    preview_data: InvoicePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a preview of the next invoice for a subscription change"""
    try:
        preview = await BillingService.get_subscription_invoice_preview(
            db, 
            str(current_user.id), 
            str(preview_data.plan_id)
        )
        return preview
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/charge")
async def create_one_time_charge(
    charge_data: OneTimeChargeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a one-time charge for the current user"""
    try:
        payment = await BillingService.create_one_time_charge(
            db, 
            str(current_user.id), 
            charge_data.amount,
            charge_data.description
        )
        return {
            "id": payment.id,
            "amount": payment.amount,
            "status": payment.status,
            "description": payment.description,
            "created_at": payment.created_at
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Stripe webhook endpoint for handling events
@router.post("/webhooks", status_code=status.HTTP_200_OK)
async def handle_stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle incoming Stripe webhook events"""
    try:
        # Get the webhook signature from headers
        signature = request.headers.get("stripe-signature")
        if not signature:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing Stripe signature"
            )
        
        # Get the raw payload
        payload = await request.body()
        
        # Verify the webhook signature
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, webhook_secret
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Stripe signature"
            )
        
        # Process the event
        event_data = event.to_dict()
        event_type = event_data.get("type")
        
        # Handle subscription-related events
        if event_type.startswith("customer.subscription"):
            await BillingService.handle_subscription_webhook(db, event_data)
        
        # Handle payment-related events
        elif event_type.startswith("payment_intent"):
            await BillingService.handle_payment_webhook(db, event_data)
        
        return {"status": "success"}
    except Exception as e:
        # Log the error but return 200 OK to Stripe
        # This prevents Stripe from retrying the webhook which could lead to duplicate processing
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}