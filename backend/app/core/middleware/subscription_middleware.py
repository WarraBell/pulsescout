# app/core/middleware/subscription_middleware.py
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.models.user import User
from app.services.subscription_service import SubscriptionService
from app.core.auth import get_current_user
import uuid
from typing import Callable, Dict
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware


class SubscriptionRequiredMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check if a user has an active subscription for protected endpoints.
    """
    
    def __init__(self, app, exclude_paths=None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or []
    
    async def dispatch(self, request: Request, call_next):
        # Skip middleware for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            return await call_next(request)
        
        # Skip middleware for non-protected paths
        if not path.startswith("/api/v1/protected"):
            return await call_next(request)
        
        # Get DB session
        db = next(get_db())
        
        try:
            # Get current user
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            # We would normally use get_current_user dependency, but middleware doesn't support dependency injection
            # So we have to extract the token and verify the user manually
            token = auth_header.replace("Bearer ", "")
            # Assuming you have a function to decode the token and get the user
            from app.core.auth import decode_token
            user_id = decode_token(token)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            # Check if user has active subscription
            has_subscription = await SubscriptionService.check_subscription_active(db, user_id)
            
            if not has_subscription:
                return HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Active subscription required"
                )
            
            # Continue with the request
            return await call_next(request)
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            # Handle other exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
        finally:
            # Close DB session
            db.close()


class FeatureAccessMiddleware(BaseHTTPMiddleware):
    """
    Middleware to check if a user's subscription plan allows access to certain features.
    """
    
    def __init__(self, app, feature_paths: Dict[str, str] = None):
        super().__init__(app)
        # Map paths to required subscription features
        # e.g., {"/api/v1/leads/export": "allows_csv_export", "/api/v1/crm/sync": "allows_crm_sync"}
        self.feature_paths = feature_paths or {}
    
    async def dispatch(self, request: Request, call_next):
        # Get path
        path = request.url.path
        
        # Check if path requires a specific feature
        required_feature = None
        for feature_path, feature in self.feature_paths.items():
            if path.startswith(feature_path):
                required_feature = feature
                break
        
        # If no feature is required, continue with the request
        if not required_feature:
            return await call_next(request)
        
        # Get DB session
        db = next(get_db())
        
        try:
            # Get current user
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            # Extract token and get user
            token = auth_header.replace("Bearer ", "")
            from app.core.auth import decode_token
            user_id = decode_token(token)
            
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials"
                )
            
            # Get subscription with plan
            subscription = await SubscriptionService.get_subscription_with_plan(db, user_id)
            
            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Active subscription required"
                )
            
            # Check if plan allows the required feature
            plan = subscription.plan
            has_feature = getattr(plan, required_feature, False)
            
            if not has_feature:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Your current plan does not include {required_feature.replace('allows_', '')} feature"
                )
            
            # Continue with the request
            return await call_next(request)
            
        except HTTPException as e:
            # Re-raise HTTP exceptions
            raise e
        except Exception as e:
            # Handle other exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal server error: {str(e)}"
            )
        finally:
            # Close DB session
            db.close()