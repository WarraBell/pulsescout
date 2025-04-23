# app/api/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.models.schemas import UserCreate, UserResponse, Token, VerifyEmail, PasswordReset, PasswordUpdate
from app.services.user_service import UserService
from app.core.security import create_access_token, verify_password, get_current_user
from app.db.session import get_db
from datetime import timedelta
import os

router = APIRouter()
user_service = UserService()

# Environment variables
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    user = await user_service.create_user(db, user_data, background_tasks)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Authenticate and login a user
    """
    user = user_service.get_user_by_email(db, form_data.username)
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.post("/verify-email")
async def verify_email(
    verify_data: VerifyEmail,
    db: Session = Depends(get_db)
):
    """
    Verify a user's email address
    """
    success = await user_service.verify_email(db, verify_data.token)
    return {"message": "Email successfully verified"}

@router.post("/forgot-password")
async def forgot_password(
    reset_data: PasswordReset,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Request a password reset
    """
    await user_service.request_password_reset(db, reset_data.email, background_tasks)
    # Always return success to prevent email enumeration
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
async def reset_password(
    password_data: PasswordUpdate,
    db: Session = Depends(get_db)
):
    """
    Reset a user's password using a token
    """
    success = await user_service.reset_password(db, password_data.token, password_data.new_password)
    return {"message": "Password successfully reset"}

@router.post("/logout")
async def logout():
    """
    Logout a user - client-side only since we're using JWT
    """
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get the current authenticated user's information
    """
    return current_user
