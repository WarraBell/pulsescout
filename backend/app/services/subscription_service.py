# app/services/subscription_service.py
import stripe
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.models.user import Subscription, Plan, User, PaymentHistory
import os
from app.utils.exceptions import SubscriptionError

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")


class SubscriptionService:
    """
    Service for handling subscription-related operations
    """
    
    @staticmethod
    async def create_subscription(db: Session, user_id: str, plan_id: str, payment_method_id: str = None):
        """
        Create a new subscription for a user
        """
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise SubscriptionError("User not found")
        
        # Get plan
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise SubscriptionError("Plan not found")
        
        try:
            # Check if user already has a stripe customer ID
            stripe_customer_id = None
            if user.subscription and user.subscription.stripe_customer_id:
                stripe_customer_id = user.subscription.stripe_customer_id
            
            # Create a new Stripe customer if needed
            if not stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email,
                    metadata={"user_id": str(user.id)}
                )
                stripe_customer_id = customer.id
            
            # Attach payment method to customer if provided
            if payment_method_id:
                stripe.PaymentMethod.attach(
                    payment_method_id,
                    customer=stripe_customer_id
                )
                
                # Set as default payment method
                stripe.Customer.modify(
                    stripe_customer_id,
                    invoice_settings={"default_payment_method": payment_method_id}
                )
            
            # Create the subscription in Stripe
            stripe_subscription = stripe.Subscription.create(
                customer=stripe_customer_id,
                items=[
                    {
                        "price": plan.stripe_price_id
                    }
                ],
                expand=["latest_invoice.payment_intent"],
                metadata={"user_id": str(user.id), "plan_id": str(plan.id)}
            )
            
            # Create or update the subscription in our database
            now = datetime.utcnow()
            subscription = db.query(Subscription).filter(Subscription.user_id == user.id).first()
            
            if subscription:
                # Update existing subscription
                subscription.plan_id = plan.id
                subscription.stripe_customer_id = stripe_customer_id
                subscription.stripe_subscription_id = stripe_subscription.id
                subscription.status = stripe_subscription.status
                subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
                subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
                subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
                subscription.leads_used_this_month = 0  # Reset lead count on plan change
                subscription.updated_at = now
            else:
                # Create new subscription
                subscription = Subscription(
                    user_id=user.id,
                    plan_id=plan.id,
                    stripe_customer_id=stripe_customer_id,
                    stripe_subscription_id=stripe_subscription.id,
                    status=stripe_subscription.status,
                    current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
                    current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
                    cancel_at_period_end=stripe_subscription.cancel_at_period_end,
                    leads_used_this_month=0,
                    created_at=now,
                    updated_at=now
                )
                db.add(subscription)
            
            # Create payment history record
            invoice = stripe_subscription.latest_invoice
            if invoice and hasattr(invoice, 'amount_paid'):
                payment_history = PaymentHistory(
                    user_id=user.id,
                    stripe_payment_id=invoice.id,
                    amount=invoice.amount_paid / 100,  # Convert from cents to dollars
                    status=invoice.status,
                    description=f"Payment for {plan.name} subscription",
                    created_at=now
                )
                db.add(payment_history)
            
            db.commit()
            db.refresh(subscription)
            return subscription
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise SubscriptionError(f"Stripe error: {str(e)}")
        except Exception as e:
            db.rollback()
            raise SubscriptionError(f"Error creating subscription: {str(e)}")
    
    @staticmethod
    async def cancel_subscription(db: Session, user_id: str, cancel_at_period_end: bool = True):
        """
        Cancel a user's subscription
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            raise SubscriptionError("No active subscription found")
        
        try:
            # Cancel in Stripe
            stripe_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=cancel_at_period_end
            )
            
            # Update in database
            subscription.status = stripe_subscription.status
            subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(subscription)
            return subscription
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise SubscriptionError(f"Stripe error: {str(e)}")
        except Exception as e:
            db.rollback()
            raise SubscriptionError(f"Error canceling subscription: {str(e)}")
    
    @staticmethod
    async def immediate_cancel_subscription(db: Session, user_id: str):
        """
        Cancel a subscription immediately instead of at period end
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            raise SubscriptionError("No active subscription found")
        
        try:
            # Cancel immediately in Stripe
            stripe.Subscription.delete(subscription.stripe_subscription_id)
            
            # Update in database
            subscription.status = "canceled"
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(subscription)
            return subscription
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise SubscriptionError(f"Stripe error: {str(e)}")
        except Exception as e:
            db.rollback()
            raise SubscriptionError(f"Error canceling subscription: {str(e)}")
    
    @staticmethod
    async def change_subscription_plan(db: Session, user_id: str, new_plan_id: str):
        """
        Change a user's subscription to a new plan
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription:
            raise SubscriptionError("No active subscription found")
        
        # Get new plan
        new_plan = db.query(Plan).filter(Plan.id == new_plan_id).first()
        if not new_plan:
            raise SubscriptionError("Plan not found")
        
        try:
            # Update subscription in Stripe
            stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            
            # Update the subscription item
            stripe_subscription = stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                items=[{
                    'id': stripe_subscription['items']['data'][0].id,
                    'price': new_plan.stripe_price_id,
                }],
                proration_behavior="always_invoice"  # or "create_prorations" based on your preference
            )
            
            # Update in database
            subscription.plan_id = new_plan.id
            subscription.status = stripe_subscription.status
            subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
            subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
            subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
            subscription.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(subscription)
            return subscription
            
        except stripe.error.StripeError as e:
            db.rollback()
            raise SubscriptionError(f"Stripe error: {str(e)}")
        except Exception as e:
            db.rollback()
            raise SubscriptionError(f"Error changing subscription: {str(e)}")
    
    @staticmethod
    async def get_subscription(db: Session, user_id: str):
        """
        Get a user's subscription
        """
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        return subscription
    
    @staticmethod
    async def get_subscription_with_plan(db: Session, user_id: str):
        """
        Get a user's subscription with plan details
        """
        subscription = db.query(Subscription).join(Plan).filter(Subscription.user_id == user_id).first()
        return subscription
    
    @staticmethod
    async def check_subscription_active(db: Session, user_id: str):
        """
        Check if a user has an active subscription
        """
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        ).first()
        return subscription is not None
    
    @staticmethod
    async def get_all_plans(db: Session):
        """
        Get all available subscription plans
        """
        plans = db.query(Plan).order_by(Plan.price).all()
        return plans
    
    @staticmethod
    async def get_plan_by_id(db: Session, plan_id: str):
        """
        Get a specific plan by ID
        """
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        return plan
    
    @staticmethod
    async def track_lead_usage(db: Session, user_id: str, count: int = 1):
        """
        Track the number of leads used by a user
        """
        subscription = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "trialing"])
        ).first()
        
        if not subscription:
            raise SubscriptionError("No active subscription found")
        
        # Get the plan details
        plan = db.query(Plan).filter(Plan.id == subscription.plan_id).first()
        if not plan:
            raise SubscriptionError("Subscription plan not found")
        
        # Check if user is within their lead limit
        if subscription.leads_used_this_month + count > plan.leads_per_month:
            raise SubscriptionError("Lead limit exceeded for current plan")
        
        # Update the lead count
        subscription.leads_used_this_month += count
        subscription.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(subscription)
        return subscription
    
    @staticmethod
    async def reset_monthly_lead_usage(db: Session):
        """
        Reset monthly lead usage for all subscriptions
        Should be called by a scheduled task at the start of each billing cycle
        """
        try:
            db.query(Subscription).update(
                {"leads_used_this_month": 0, "updated_at": datetime.utcnow()},
                synchronize_session=False
            )
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise SubscriptionError(f"Error resetting monthly usage: {str(e)}")
    
    @staticmethod
    async def handle_subscription_webhook(db: Session, event_data):
        """
        Handle Stripe webhook events related to subscriptions
        """
        event_type = event_data.get("type")
        
        if event_type == "customer.subscription.created":
            # A new subscription was created
            subscription_data = event_data.get("data", {}).get("object", {})
            user_id = subscription_data.get("metadata", {}).get("user_id")
            
            if not user_id:
                return False
                
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_data.get("id")
            ).first()
            
            if not subscription:
                # Create new subscription record
                plan_id = subscription_data.get("metadata", {}).get("plan_id")
                plan = db.query(Plan).filter(Plan.stripe_price_id == subscription_data.get("plan", {}).get("id")).first()
                
                if not plan and not plan_id:
                    return False
                    
                subscription = Subscription(
                    user_id=user_id,
                    plan_id=plan_id if plan_id else plan.id,
                    stripe_customer_id=subscription_data.get("customer"),
                    stripe_subscription_id=subscription_data.get("id"),
                    status=subscription_data.get("status"),
                    current_period_start=datetime.fromtimestamp(subscription_data.get("current_period_start")),
                    current_period_end=datetime.fromtimestamp(subscription_data.get("current_period_end")),
                    cancel_at_period_end=subscription_data.get("cancel_at_period_end"),
                    leads_used_this_month=0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(subscription)
                db.commit()
                
        elif event_type == "customer.subscription.updated":
            # An existing subscription was updated
            subscription_data = event_data.get("data", {}).get("object", {})
            
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_data.get("id")
            ).first()
            
            if subscription:
                # Update subscription record
                subscription.status = subscription_data.get("status")
                subscription.current_period_start = datetime.fromtimestamp(subscription_data.get("current_period_start"))
                subscription.current_period_end = datetime.fromtimestamp(subscription_data.get("current_period_end"))
                subscription.cancel_at_period_end = subscription_data.get("cancel_at_period_end")
                subscription.updated_at = datetime.utcnow()
                
                # Check if plan changed
                stripe_price_id = subscription_data.get("items", {}).get("data", [])[0].get("price", {}).get("id")
                if stripe_price_id:
                    plan = db.query(Plan).filter(Plan.stripe_price_id == stripe_price_id).first()
                    if plan and plan.id != subscription.plan_id:
                        subscription.plan_id = plan.id
                        subscription.leads_used_this_month = 0  # Reset lead count on plan change
                
                db.commit()
                
        elif event_type == "customer.subscription.deleted":
            # A subscription was cancelled
            subscription_data = event_data.get("data", {}).get("object", {})
            
            subscription = db.query(Subscription).filter(
                Subscription.stripe_subscription_id == subscription_data.get("id")
            ).first()
            
            if subscription:
                # Update subscription status
                subscription.status = "canceled"
                subscription.updated_at = datetime.utcnow()
                db.commit()
                
        return True