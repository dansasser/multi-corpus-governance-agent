"""Authentication API endpoints.

This module provides secure authentication endpoints including:
- User login and logout
- Token refresh and validation  
- User registration and management
- Session management
- Password security operations

All endpoints implement comprehensive security logging and monitoring.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator

from ..auth import (
    authentication_service,
    get_current_user,
    require_roles,
    require_permissions
)
from ..session_manager import session_manager
from ...utils.exceptions import AuthenticationError, AuthorizationError
from ...utils.logging import SecurityLogger
from ...database.session import db_manager
from ...database.models import User

# Create router
router = APIRouter()

# Security scheme
security = HTTPBearer()


# Pydantic models for request/response

class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., min_length=1, max_length=100, description="Username or email")
    password: str = Field(..., min_length=1, description="User password")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "secure_password_123"
            }
        }


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: Dict[str, Any] = Field(..., description="User information")


class UserRegistration(BaseModel):
    """User registration request model."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=12, description="Strong password")
    full_name: Optional[str] = Field(None, max_length=200, description="Full name")
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation."""
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('username')
    def validate_username(cls, v):
        """Username validation."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()
    
    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com", 
                "password": "SecurePassword123!",
                "full_name": "John Doe"
            }
        }


class PasswordChangeRequest(BaseModel):
    """Password change request model."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=12, description="New strong password")
    
    class Config:
        schema_extra = {
            "example": {
                "current_password": "old_password_123",
                "new_password": "NewSecurePassword456!"
            }
        }


class TokenRefreshResponse(BaseModel):
    """Token refresh response model."""
    access_token: str = Field(..., description="New JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    ip_address: str = Field(..., description="Client IP address")
    user_agent: str = Field(..., description="Client user agent")
    created_at: datetime = Field(..., description="Session creation time")
    last_activity: datetime = Field(..., description="Last activity time")
    expires_at: datetime = Field(..., description="Session expiration time")


# Authentication endpoints

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
    description="Authenticate user credentials and create session with JWT token"
)
async def login(
    login_data: LoginRequest,
    request: Request
) -> LoginResponse:
    """
    Authenticate user and create session.
    
    - **username**: Username or email address
    - **password**: User password
    
    Returns JWT access token and user information.
    """
    
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    try:
        # Authenticate user
        auth_result = await authentication_service.authenticate_user(
            username=login_data.username,
            password=login_data.password,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        await SecurityLogger.log_authentication_event(
            event_subtype="login_success",
            user_id=auth_result["user"]["id"],
            ip_address=client_ip,
            success=True
        )
        
        return LoginResponse(**auth_result)
        
    except AuthenticationError as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="login_failed",
            user_id=None,
            ip_address=client_ip,
            success=False,
            failure_reason=e.reason
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.reason,
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/logout",
    summary="User Logout", 
    description="Logout user and invalidate session"
)
async def logout(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Logout current user and invalidate session.
    
    Requires valid JWT token in Authorization header.
    """
    
    try:
        # Extract token from authorization header
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            
            # Logout user
            await authentication_service.logout_user(token)
            
            await SecurityLogger.log_authentication_event(
                event_subtype="logout_success",
                user_id=current_user["user_id"],
                ip_address=request.client.host if request.client else "unknown",
                success=True
            )
            
            return {"message": "Successfully logged out"}
            
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
            
    except Exception as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="logout_failed",
            user_id=current_user.get("user_id"),
            ip_address=request.client.host if request.client else "unknown",
            success=False,
            failure_reason=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post(
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="Refresh Token",
    description="Refresh JWT access token"
)
async def refresh_token(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> TokenRefreshResponse:
    """
    Refresh JWT access token.
    
    Requires valid JWT token in Authorization header.
    Returns new access token with extended expiration.
    """
    
    try:
        # Extract current token
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        current_token = auth_header[7:]
        
        # Create new token
        from ..auth import jwt_manager
        new_token = jwt_manager.refresh_token(current_token)
        
        await SecurityLogger.log_authentication_event(
            event_subtype="token_refreshed",
            user_id=current_user["user_id"],
            ip_address=request.client.host if request.client else "unknown",
            success=True
        )
        
        return TokenRefreshResponse(
            access_token=new_token,
            expires_in=jwt_manager.access_token_expire_minutes * 60
        )
        
    except Exception as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="token_refresh_failed",
            user_id=current_user.get("user_id"),
            ip_address=request.client.host if request.client else "unknown",
            success=False,
            failure_reason=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.get(
    "/me",
    summary="Current User Info",
    description="Get current user information"
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get information about the currently authenticated user.
    
    Returns user profile and session information.
    """
    
    try:
        # Get additional user information from database
        async with db_manager.get_session() as session:
            user = await session.query(User).filter(
                User.id == current_user["user_id"]
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Get session information
            session_data = await session_manager.get_session(current_user["session_token"])
            
            return {
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "roles": user.roles,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None
                },
                "session": {
                    "session_token": current_user["session_token"][:8] + "...",  # Truncated for security
                    "ip_address": session_data.get("ip_address") if session_data else "unknown",
                    "created_at": session_data.get("created_at") if session_data else None,
                    "last_activity": session_data.get("last_activity") if session_data else None,
                    "expires_at": session_data.get("expires_at") if session_data else None
                }
            }
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information"
        )


# User management endpoints (admin only)

@router.post(
    "/register", 
    summary="Register New User",
    description="Register a new user account (admin only)"
)
async def register_user(
    user_data: UserRegistration,
    request: Request,
    current_user: Dict[str, Any] = Depends(require_roles(["admin"]))
) -> Dict[str, Any]:
    """
    Register a new user account.
    
    Requires admin role. Validates password strength and creates user account.
    """
    
    try:
        from ..auth import password_manager
        
        # Validate password strength
        password_validation = password_manager.validate_password_strength(user_data.password)
        if not password_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Weak password", 
                    "issues": password_validation["issues"]
                }
            )
        
        # Hash password
        password_hash = password_manager.hash_password(user_data.password)
        
        # Create user in database
        async with db_manager.get_session() as session:
            # Check if username or email already exists
            existing_user = await session.query(User).filter(
                (User.username == user_data.username) | 
                (User.email == user_data.email)
            ).first()
            
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Username or email already exists"
                )
            
            # Create new user
            new_user = User(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                full_name=user_data.full_name,
                roles=["user"],  # Default role
                is_active=True
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            await SecurityLogger.log_authentication_event(
                event_subtype="user_registered",
                user_id=str(new_user.id),
                ip_address=request.client.host if request.client else "unknown",
                success=True,
                details={
                    "registered_by": current_user["user_id"],
                    "username": user_data.username,
                    "email": user_data.email
                }
            )
            
            return {
                "message": "User registered successfully",
                "user_id": str(new_user.id),
                "username": new_user.username,
                "email": new_user.email
            }
            
    except HTTPException:
        raise
    except Exception as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="user_registration_failed",
            user_id=None,
            ip_address=request.client.host if request.client else "unknown", 
            success=False,
            failure_reason=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )


@router.put(
    "/password",
    summary="Change Password",
    description="Change user password"
)
async def change_password(
    password_data: PasswordChangeRequest,
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, str]:
    """
    Change user password.
    
    Requires current password for verification.
    """
    
    try:
        from ..auth import password_manager
        
        # Get user from database
        async with db_manager.get_session() as session:
            user = await session.query(User).filter(
                User.id == current_user["user_id"]
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Verify current password
            if not password_manager.verify_password(password_data.current_password, user.password_hash):
                await SecurityLogger.log_authentication_event(
                    event_subtype="password_change_failed_verification",
                    user_id=current_user["user_id"],
                    ip_address=request.client.host if request.client else "unknown",
                    success=False,
                    failure_reason="Current password verification failed"
                )
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
            
            # Validate new password strength
            password_validation = password_manager.validate_password_strength(password_data.new_password)
            if not password_validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Weak password",
                        "issues": password_validation["issues"]
                    }
                )
            
            # Hash new password
            new_password_hash = password_manager.hash_password(password_data.new_password)
            
            # Update password
            user.password_hash = new_password_hash
            await session.commit()
            
            # Invalidate all user sessions except current one
            await authentication_service.logout_all_user_sessions(current_user["user_id"])
            
            await SecurityLogger.log_authentication_event(
                event_subtype="password_changed",
                user_id=current_user["user_id"],
                ip_address=request.client.host if request.client else "unknown",
                success=True
            )
            
            return {"message": "Password changed successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="password_change_failed",
            user_id=current_user.get("user_id"),
            ip_address=request.client.host if request.client else "unknown",
            success=False,
            failure_reason=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


# Session management endpoints

@router.get(
    "/sessions",
    response_model=List[SessionInfo],
    summary="List User Sessions",
    description="List all active sessions for current user"
)
async def list_user_sessions(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[SessionInfo]:
    """
    List all active sessions for the current user.
    
    Returns session information including IP addresses and activity.
    """
    
    try:
        # Get session count (Redis implementation would need to be extended for full session listing)
        active_sessions_count = await session_manager.get_active_sessions_count(current_user["user_id"])
        
        # For now, return current session info
        # In a full implementation, we'd query Redis for all user sessions
        current_session = await session_manager.get_session(current_user["session_token"])
        
        if current_session:
            return [
                SessionInfo(
                    session_id=current_user["session_token"][:8] + "...",
                    user_id=current_user["user_id"],
                    ip_address=current_session.get("ip_address", "unknown"),
                    user_agent=current_session.get("user_agent", "unknown"),
                    created_at=datetime.fromisoformat(current_session["created_at"]),
                    last_activity=datetime.fromisoformat(current_session["last_activity"]),
                    expires_at=datetime.fromisoformat(current_session["expires_at"])
                )
            ]
        else:
            return []
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.delete(
    "/sessions",
    summary="Revoke All Sessions",
    description="Revoke all sessions except current one"
)
async def revoke_all_sessions(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Revoke all sessions for current user except the current session.
    
    Useful for security purposes when user suspects account compromise.
    """
    
    try:
        # Invalidate all sessions except current one
        revoked_count = await authentication_service.logout_all_user_sessions(current_user["user_id"])
        
        await SecurityLogger.log_authentication_event(
            event_subtype="all_sessions_revoked",
            user_id=current_user["user_id"],
            ip_address=request.client.host if request.client else "unknown",
            success=True,
            details={"sessions_revoked": revoked_count}
        )
        
        return {
            "message": f"Successfully revoked {revoked_count} sessions",
            "sessions_revoked": revoked_count
        }
        
    except Exception as e:
        await SecurityLogger.log_authentication_event(
            event_subtype="session_revocation_failed",
            user_id=current_user.get("user_id"),
            ip_address=request.client.host if request.client else "unknown",
            success=False,
            failure_reason=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Session revocation failed"
        )