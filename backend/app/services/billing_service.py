# app/services/billing_service.py
import stripe
from datetime import datetime
from sqlalchemy.orm import Session
from app.api.models.user import Subscription, Plan, User, PaymentHistory
import os
from app.utils.exceptions import BillingError

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_API_KEY")


class BillingService:
    """
    Service for handling billing and payment operations
    """
    
    @staticmethod
    async def create_setup_intent(db: Session, user_id: str):
        """
        Create a SetupIntent for securely collecting payment method details
        """
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise BillingError("User not found")
        
        try:
            # Check if user already has a stripe customer ID
            stripe_customer_id = None
            subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
            
            if subscription and subscription.stripe_customer_id:
                stripe_customer_id = subscription.stripe_customer_id
            
            # Create a new Stripe customer if needed
            if not stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email,
                    metadata={"user_id": str(user.id)}
                )
                stripe_customer_id = customer.id
                
                # Save customer ID if subscription exists
                if subscription:
                    subscription.stripe_customer_id = stripe_customer_id
                    subscription.updated_at = datetime.utcnow()
                    db.commit()
            
            # Create SetupIntent
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer_id,
                payment_method_types=["card"],
                usage="off_session",
            )
            
            return {
                "client_secret": setup_intent.client_secret,
                "customer_id": stripe_customer_id
            }
            
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error creating setup intent: {str(e)}")
    
    @staticmethod
    async def get_payment_methods(db: Session, user_id: str):
        """
        Get all payment methods for a user
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription or not subscription.stripe_customer_id:
            return []
        
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=subscription.stripe_customer_id,
                type="card"
            )
            
            # Format payment methods
            formatted_payment_methods = []
            for pm in payment_methods.data:
                card = pm.card
                formatted_payment_methods.append({
                    "id": pm.id,
                    "brand": card.brand,
                    "last4": card.last4,
                    "exp_month": card.exp_month,
                    "exp_year": card.exp_year,
                    "is_default": pm.id == subscription.default_payment_method
                })
                
            return formatted_payment_methods
            
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error retrieving payment methods: {str(e)}")
    
    @staticmethod
    async def update_default_payment_method(db: Session, user_id: str, payment_method_id: str):
        """
        Update the default payment method for a user
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription or not subscription.stripe_customer_id:
            raise BillingError("No active subscription found")
        
        try:
            # Update the default payment method in Stripe
            stripe.Customer.modify(
                subscription.stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
            
            return {"success": True}
            
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error updating payment method: {str(e)}")
    
    @staticmethod
    async def remove_payment_method(db: Session, user_id: str, payment_method_id: str):
        """
        Remove a payment method for a user
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription or not subscription.stripe_customer_id:
            raise BillingError("No active subscription found")
        
        try:
            # Check if it's the default payment method
            customer = stripe.Customer.retrieve(
                subscription.stripe_customer_id,
                expand=["invoice_settings.default_payment_method"]
            )
            
            is_default = (
                customer.invoice_settings.default_payment_method and 
                customer.invoice_settings.default_payment_method.id == payment_method_id
            )
            
            if is_default:
                raise BillingError("Cannot remove default payment method. Please set another payment method as default first.")
            
            # Detach the payment method
            stripe.PaymentMethod.detach(payment_method_id)
            
            return {"success": True}
            
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error removing payment method: {str(e)}")
    
    @staticmethod
    async def get_payment_history(db: Session, user_id: str, limit: int = 10, offset: int = 0):
        """
        Get payment history for a user
        """
        payment_history = db.query(PaymentHistory).filter(
            PaymentHistory.user_id == user_id
        ).order_by(
            PaymentHistory.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return payment_history
    
    @staticmethod
    async def get_subscription_invoice_preview(db: Session, user_id: str, plan_id: str):
        """
        Get a preview of the next invoice for a subscription change
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription or not subscription.stripe_customer_id:
            raise BillingError("No active subscription found")
        
        # Get new plan
        new_plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not new_plan:
            raise BillingError("Plan not found")
        
        try:
            # Get the upcoming invoice
            upcoming_invoice = stripe.Invoice.upcoming(
                customer=subscription.stripe_customer_id,
                subscription=subscription.stripe_subscription_id,
                subscription_items=[{
                    'id': stripe.Subscription.retrieve(subscription.stripe_subscription_id)['items']['data'][0].id,
                    'price': new_plan.stripe_price_id,
                }],
                subscription_proration_date=int(datetime.utcnow().timestamp())
            )
            
            # Format the invoice preview
            total = upcoming_invoice.total / 100
            proration_amount = 0
            
            for line in upcoming_invoice.lines.data:
                if line.get('proration'):
                    proration_amount += line.amount / 100
            
            return {
                "total": total,
                "proration_amount": proration_amount,
                "next_billing_date": datetime.fromtimestamp(upcoming_invoice.period_end),
                "currency": upcoming_invoice.currency
            }
            
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error generating invoice preview: {str(e)}")
    
    @staticmethod
    async def create_one_time_charge(db: Session, user_id: str, amount: float, description: str):
        """
        Create a one-time charge for a user
        """
        # Get user's subscription
        subscription = db.query(Subscription).filter(Subscription.user_id == user_id).first()
        if not subscription or not subscription.stripe_customer_id:
            raise BillingError("No active subscription or payment method found")
        
        try:
            # Create a payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency="usd",
                customer=subscription.stripe_customer_id,
                description=description,
                confirm=True,
                off_session=True,
                metadata={"user_id": str(user_id)}
            )
            
            # Create payment history record
            payment_history = PaymentHistory(
                user_id=user_id,
                stripe_payment_id=payment_intent.id,
                amount=amount,
                status=payment_intent.status,
                description=description,
                created_at=datetime.utcnow()
            )
            db.add(payment_history)
            db.commit()
            
            return payment_history
            
        except stripe.error.CardError as e:
            raise BillingError(f"Card declined: {e.error.message}")
        except stripe.error.StripeError as e:
            raise BillingError(f"Stripe error: {str(e)}")
        except Exception as e:
            raise BillingError(f"Error processing payment: {str(e)}")
    
    @staticmethod
    async def handle_payment_webhook(db: Session, event_data):
        """
        Handle Stripe webhook events related to payments
        """
        event_type = event_data.get("type")
        
        if event_type == "payment_intent.succeeded":
            # Payment succeeded
            payment_data = event_data.get("data", {}).get("object", {})
            user_id = payment_data.get("metadata", {}).get("user_id")
            
            if not user_id:
                return False
                
            # Check if payment already recorded
            existing_payment = db.query(PaymentHistory).filter(
                PaymentHistory.stripe_payment_id == payment_data.get("id")
            ).first()
            
            if not existing_payment:
                # Create new payment record
                payment_history = PaymentHistory(
                    user_id=user_id,
                    stripe_payment_id=payment_data.get("id"),
                    amount=payment_data.get("amount") / 100,  # Convert from cents
                    status=payment_data.get("status"),
                    description=payment_data.get("description"),
                    created_at=datetime.utcnow()
                )
                db.add(payment_history)
                db.commit()
                
        elif event_type == "payment_intent.payment_failed":
            # Payment failed
            payment_data = event_data.get("data", {}).get("object", {})
            user_id = payment_data.get("metadata", {}).get("user_id")
            
            if not user_id:
                return False
                
            # Create failed payment record
            payment_history = PaymentHistory(
                user_id=user_id,
                stripe_payment_id=payment_data.get("id"),
                amount=payment_data.get("amount") / 100,  # Convert from cents
                status="failed",
                description=f"Failed payment: {payment_data.get('description')}",
                created_at=datetime.utcnow()
            )
            db.add(payment_history)
            db.commit()
                
        return True