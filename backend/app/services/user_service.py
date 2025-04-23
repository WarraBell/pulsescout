# app/services/user_service.py
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, BackgroundTasks
from app.api.models.user import User, Plan, Subscription
from app.api.models.schemas import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password, generate_verification_token
from app.services.email_service import EmailService
import uuid
from datetime import datetime, timedelta

class UserService:
    def __init__(self):
        self.email_service = EmailService()
    
    async def create_user(self, db: Session, user_data: UserCreate, background_tasks: BackgroundTasks) -> User:
        """
        Create a new user and send verification email
        """
        # Check if user with this email already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create verification token
        verification_token = generate_verification_token()
        
        # Hash the password
        hashed_password = get_password_hash(user_data.password)
        
        # Create the user object
        db_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            password_hash=hashed_password,
            is_active=True,
            is_verified=False,
            verification_token=verification_token,
            company_name=user_data.company_name,
            industry=user_data.industry,
            company_size=user_data.company_size,
            job_title=user_data.job_title,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add user to database
        db.add(db_user)
        
        # Create a free trial subscription for the user
        free_trial_plan = db.query(Plan).filter(Plan.name == "Free Trial").first()
        if not free_trial_plan:
            # Create a default free trial plan if it doesn't exist
            free_trial_plan = Plan(
                id=uuid.uuid4(),
                name="Free Trial",
                description="Limited to 25 leads/month with basic filters only",
                price=0.0,
                billing_interval="month",
                leads_per_month=25,
                allows_csv_export=False,
                allows_crm_sync=False,
                allows_team_access=False,
                allows_api_access=False,
                allows_white_labeling=False,
                allows_enrichment=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(free_trial_plan)
            db.flush()  # Generate ID for the plan
        
        # Create subscription
        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=db_user.id,
            plan_id=free_trial_plan.id,
            status="active",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),  # 30-day free trial
            cancel_at_period_end=True,  # Auto-cancel after free trial
            leads_used_this_month=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(subscription)
        
        # Commit the transaction
        db.commit()
        db.refresh(db_user)
        
        # Send verification email in the background
        background_tasks.add_task(
            self.email_service.send_verification_email,
            user_data.email,
            verification_token
        )
        
        return db_user
    
    async def verify_email(self, db: Session, token: str) -> bool:
        """
        Verify a user's email address using a token
        """
        user = db.query(User).filter(User.verification_token == token).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        # Update user verification status
        user.is_verified = True
        user.verification_token = None  # Clear the token
        user.updated_at = datetime.utcnow()
        
        db.commit()
        return True
    
    async def request_password_reset(self, db: Session, email: str, background_tasks: BackgroundTasks) -> bool:
        """
        Request a password reset for a user
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Don't reveal that the user doesn't exist
            return True
        
        # Generate a password reset token
        reset_token = generate_verification_token()
        
        # Store the token in the user record
        user.verification_token = reset_token
        user.updated_at = datetime.utcnow()
        db.commit()
        
        # Send password reset email in the background
        background_tasks.add_task(
            self.email_service.send_password_reset_email,
            email,
            reset_token
        )
        
        return True
    
    async def reset_password(self, db: Session, token: str, new_password: str) -> bool:
        """
        Reset a user's password using a token
        """
        user = db.query(User).filter(User.verification_token == token).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        hashed_password = get_password_hash(new_password)
        user.password_hash = hashed_password
        user.verification_token = None  # Clear the token
        user.updated_at = datetime.utcnow()
        
        db.commit()
        return True
    
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """
        Get a user by email
        """
        return db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, db: Session, user_id: uuid.UUID) -> Optional[User]:
        """
        Get a user by ID
        """
        return db.query(User).filter(User.id == user_id).first()