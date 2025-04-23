# app/api/endpoints/subscription.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.models.user import User, Subscription, Plan
from app.core.auth import get_current_user
from app.db.database import get_db
from app.services.subscription_service import SubscriptionService
from typing import List
import uuid
from pydantic import BaseModel, UUID4, Field

router = APIRouter()

# Pydantic models for request/response validation
class PlanResponse(BaseModel):
    id: UUID4
    name: str
    description: str = None
    price: float
    billing_interval: str
    features: List[str] = None
    leads_per_month: int
    allows_csv_export: bool
    allows_crm_sync: bool
    allows_team_access: bool
    max_team_members: int
    allows_api_access: bool
    allows_white_labeling: bool
    allows_enrichment: bool
    
    class Config:
        orm_mode = True

class SubscriptionResponse(BaseModel):
    id: UUID4
    plan: PlanResponse
    status: str
    current_period_start: str = None
    current_period_end: str = None
    cancel_at_period_end: bool
    leads_used_this_month: int
    leads_remaining: int
    
    class Config:
        orm_mode = True

class SubscriptionCreateRequest(BaseModel):
    plan_id: UUID4
    payment_method_id: str = None

class SubscriptionUpdateRequest(BaseModel):
    plan_id: UUID4

class CancelSubscriptionRequest(BaseModel):
    cancel_at_period_end: bool = True


@router.get("/plans", response_model=List[PlanResponse])
async def get_plans(db: Session = Depends(get_db)):
    """Get all available subscription plans"""
    plans = await SubscriptionService.get_all_plans(db)
    return plans


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_user_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's subscription"""
    subscription = await SubscriptionService.get_subscription_with_plan(db, current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Calculate leads remaining
    leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
    
    # Create response with additional calculated fields
    subscription_data = {
        "id": subscription.id,
        "plan": subscription.plan,
        "status": subscription.status,
        "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
        "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "leads_used_this_month": subscription.leads_used_this_month,
        "leads_remaining": leads_remaining
    }
    
    return subscription_data


@router.post("/subscription", response_model=SubscriptionResponse)
async def create_subscription(
    subscription_data: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new subscription for the current user"""
    try:
        subscription = await SubscriptionService.create_subscription(
            db, 
            str(current_user.id), 
            str(subscription_data.plan_id),
            subscription_data.payment_method_id
        )
        
        # Calculate leads remaining
        leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
        
        # Create response with additional calculated fields
        subscription_data = {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "leads_used_this_month": subscription.leads_used_this_month,
            "leads_remaining": leads_remaining
        }
        
        return subscription_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/subscription", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_data: SubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change the current user's subscription plan"""
    try:
        subscription = await SubscriptionService.change_subscription_plan(
            db, 
            str(current_user.id), 
            str(subscription_data.plan_id)
        )
        
        # Calculate leads remaining
        leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
        
        # Create response with additional calculated fields
        subscription_data = {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "leads_used_this_month": subscription.leads_used_this_month,
            "leads_remaining": leads_remaining
        }
        
        return subscription_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    cancel_data: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel the current user's subscription"""
    try:
        subscription = await SubscriptionService.cancel_subscription(
            db, 
            str(current_user.id), 
            cancel_data.cancel_at_period_end
        )
        
        # Calculate leads remaining
        leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
        
        # Create response with additional calculated fields
        subscription_data = {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "leads_used_this_month": subscription.leads_used_this_month,
            "leads_remaining": leads_remaining
        }
        
        return subscription_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/subscription/cancel-immediately", response_model=SubscriptionResponse)
async def cancel_subscription_immediately(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel the current user's subscription immediately"""
    try:
        subscription = await SubscriptionService.immediate_cancel_subscription(
            db, 
            str(current_user.id)
        )
        
        # Calculate leads remaining
        leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
        
        # Create response with additional calculated fields
        subscription_data = {
            "id": subscription.id,
            "plan": subscription.plan,
            "status": subscription.status,
            "current_period_start": subscription.current_period_start.isoformat() if subscription.current_period_start else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "leads_used_this_month": subscription.leads_used_this_month,
            "leads_remaining": leads_remaining
        }
        
        return subscription_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/subscription/usage")
async def get_subscription_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current user's subscription usage details"""
    subscription = await SubscriptionService.get_subscription_with_plan(db, current_user.id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No subscription found"
        )
    
    # Calculate leads remaining and usage percentage
    leads_remaining = subscription.plan.leads_per_month - subscription.leads_used_this_month
    usage_percentage = (subscription.leads_used_this_month / subscription.plan.leads_per_month) * 100 if subscription.plan.leads_per_month > 0 else 0
    
    return {
        "plan_name": subscription.plan.name,
        "leads_used": subscription.leads_used_this_month,
        "leads_total": subscription.plan.leads_per_month,
        "leads_remaining": leads_remaining,
        "usage_percentage": round(usage_percentage, 2)
    }