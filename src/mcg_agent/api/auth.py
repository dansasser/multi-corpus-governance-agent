"""JWT Authentication system for Multi-Corpus Governance Agent.

This module implements secure JWT-based authentication with role-based
access control following security requirements from:
docs/security/architecture/security-architecture.md
docs/security/protocols/governance-protocol.md
"""

import jwt
import bcrypt
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any, Union
from uuid import uuid4

from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from ..config import settings
from ..utils.exceptions import (
    AuthenticationError, 
    AuthorizationError,
    SecurityValidationError
)
from ..utils.logging import SecurityLogger
from ..database.session import db_manager
from ..database.models import User, UserSession
from .session_manager import session_manager


class JWTManager:
    """
    Secure JWT token management with role-based access control.
    
    Implements security requirements from security documentation including:
    - Strong cryptographic signatures
    - Short token expiration times  
    - Comprehensive audit logging
    - Role-based permission checking
    """
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY.get_secret_value()
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        
        # Validate JWT secret strength
        if len(self.secret_key) < 32:
            raise SecurityValidationError(
                validation_type="jwt_secret_strength",
                details={"minimum_length": 32, "current_length": len(self.secret_key)}
            )
    
    def create_access_token(
        self, 
        user_data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token with user data and permissions.
        
        Args:
            user_data: User information and roles
            expires_delta: Custom expiration time
            
        Returns:
            Encoded JWT token
        """
        to_encode = user_data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )
        
        # Add standard JWT claims
        to_encode.update({
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'iss': 'mcg-agent',  # Issuer
            'aud': 'mcg-agent-api',  # Audience
            'jti': str(uuid4()),  # JWT ID for tracking
            'sub': str(user_data['user_id']),  # Subject
            'type': 'access'
        })
        
        # Create token
        try:
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            # Log token creation (without sensitive data)
            asyncio.create_task(SecurityLogger.log_authentication_event(
                event_subtype="token_created",
                user_id=user_data['user_id'],
                ip_address=user_data.get('ip_address', 'unknown'),
                success=True
            ))
            
            return encoded_jwt
            
        except Exception as e:
            asyncio.create_task(SecurityLogger.log_authentication_event(
                event_subtype="token_creation_failed", 
                user_id=user_data['user_id'],
                ip_address=user_data.get('ip_address', 'unknown'),
                success=False,
                failure_reason=str(e)
            ))
            raise AuthenticationError(
                reason=f"Token creation failed: {str(e)}",
                details={"user_id": user_data['user_id']}
            )
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token with security validation.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token payload
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience='mcg-agent-api',
                issuer='mcg-agent'
            )
            
            # Validate token type
            if payload.get('type') != 'access':
                raise AuthenticationError(
                    reason="Invalid token type",
                    details={"expected": "access", "received": payload.get('type')}
                )
            
            # Check expiration (additional to JWT library check)
            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, timezone.utc)
                if datetime.now(timezone.utc) > exp_datetime:
                    raise AuthenticationError(
                        reason="Token expired",
                        details={"expired_at": exp_datetime.isoformat()}
                    )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                reason="Token expired",
                details={"token_preview": token[:20] + "..."}
            )
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(
                reason=f"Invalid token: {str(e)}",
                details={"token_preview": token[:20] + "..."}
            )
        except Exception as e:
            raise AuthenticationError(
                reason=f"Token verification failed: {str(e)}",
                details={"token_preview": token[:20] + "..."}
            )
    
    def refresh_token(self, token: str) -> str:
        """
        Refresh JWT token with new expiration.
        
        Args:
            token: Current valid token
            
        Returns:
            New token with extended expiration
        """
        try:
            # Verify current token
            payload = self.verify_token(token)
            
            # Create new token with same data but new expiration
            user_data = {
                'user_id': payload['sub'],
                'username': payload['username'],
                'roles': payload['roles'],
                'permissions': payload.get('permissions', {}),
                'ip_address': payload.get('ip_address', 'unknown')
            }
            
            return self.create_access_token(user_data)
            
        except Exception as e:
            raise AuthenticationError(
                reason=f"Token refresh failed: {str(e)}",
                details={"token_preview": token[:20] + "..."}
            )


class PasswordManager:
    """Secure password hashing and verification."""
    
    def __init__(self):
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12  # Strong hashing rounds
        )
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with strong rounds."""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Validate password meets security requirements.
        
        Returns:
            Validation result with strength indicators
        """
        issues = []
        strength_score = 0
        
        # Length check
        if len(password) < 12:
            issues.append("Password must be at least 12 characters")
        else:
            strength_score += 2
        
        # Character variety checks
        if not any(c.isupper() for c in password):
            issues.append("Password must contain uppercase letters")
        else:
            strength_score += 1
            
        if not any(c.islower() for c in password):
            issues.append("Password must contain lowercase letters")
        else:
            strength_score += 1
            
        if not any(c.isdigit() for c in password):
            issues.append("Password must contain numbers")
        else:
            strength_score += 1
            
        if not any(c in "!@#$%^&*(),.?\":{}|<>" for c in password):
            issues.append("Password must contain special characters")
        else:
            strength_score += 1
        
        # Common password check (basic)
        common_passwords = [
            "password", "123456", "password123", "admin", "qwerty",
            "letmein", "welcome", "monkey", "dragon"
        ]
        if password.lower() in common_passwords:
            issues.append("Password is too common")
            strength_score = 0
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "strength_score": min(strength_score, 6),  # Max 6
            "strength_level": self._get_strength_level(strength_score)
        }
    
    def _get_strength_level(self, score: int) -> str:
        """Convert numeric score to strength level."""
        if score >= 5:
            return "strong"
        elif score >= 3:
            return "medium"
        elif score >= 1:
            return "weak"
        else:
            return "very_weak"


class AuthenticationService:
    """
    Complete authentication service with user management,
    session tracking, and security monitoring.
    """
    
    def __init__(self):
        self.jwt_manager = JWTManager()
        self.password_manager = PasswordManager()
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authenticate user credentials and create session.
        
        Args:
            username: Username or email
            password: Plain text password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Authentication result with token and user data
        """
        try:
            # Get user from database
            async with db_manager.get_session() as session:
                # Try username first, then email
                user = await session.query(User).filter(
                    (User.username == username) | (User.email == username)
                ).first()
                
                if not user:
                    await SecurityLogger.log_authentication_event(
                        event_subtype="user_not_found",
                        user_id=None,
                        ip_address=ip_address,
                        success=False,
                        failure_reason=f"User not found: {username}"
                    )
                    raise AuthenticationError(
                        reason="Invalid credentials",
                        details={"username": username}
                    )
                
                # Check if user is active
                if not user.is_active:
                    await SecurityLogger.log_authentication_event(
                        event_subtype="inactive_user_login_attempt",
                        user_id=str(user.id),
                        ip_address=ip_address,
                        success=False,
                        failure_reason="User account is inactive"
                    )
                    raise AuthenticationError(
                        reason="Account is inactive",
                        details={"user_id": str(user.id)}
                    )
                
                # Check if account is locked
                if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                    await SecurityLogger.log_authentication_event(
                        event_subtype="locked_account_login_attempt",
                        user_id=str(user.id),
                        ip_address=ip_address,
                        success=False,
                        failure_reason=f"Account locked until {user.locked_until}"
                    )
                    raise AuthenticationError(
                        reason="Account is temporarily locked",
                        details={
                            "user_id": str(user.id),
                            "locked_until": user.locked_until.isoformat()
                        }
                    )
                
                # Verify password
                if not self.password_manager.verify_password(password, user.password_hash):
                    # Increment failed login attempts
                    user.failed_login_attempts += 1
                    
                    # Lock account after 5 failed attempts
                    if user.failed_login_attempts >= 5:
                        user.locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
                    
                    await session.commit()
                    
                    await SecurityLogger.log_authentication_event(
                        event_subtype="password_verification_failed",
                        user_id=str(user.id),
                        ip_address=ip_address,
                        success=False,
                        failure_reason=f"Failed attempt #{user.failed_login_attempts}"
                    )
                    
                    raise AuthenticationError(
                        reason="Invalid credentials",
                        details={"user_id": str(user.id)}
                    )
                
                # Successful authentication - reset failed attempts
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.now(timezone.utc)
                await session.commit()
                
                # Create Redis session
                session_data = {
                    'user_id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'roles': user.roles or ['user'],
                    'permissions': user.permissions or {},
                    'ip_address': ip_address,
                    'user_agent': user_agent or "Unknown"
                }
                
                session_token = await session_manager.create_session(
                    user_id=str(user.id),
                    user_data=session_data,
                    expires_in=86400  # 24 hours
                )
                
                # Create JWT token
                user_data = {
                    'user_id': str(user.id),
                    'username': user.username,
                    'email': user.email,
                    'roles': user.roles or ['user'],
                    'permissions': user.permissions or {},
                    'session_token': session_token,
                    'ip_address': ip_address
                }
                
                access_token = self.jwt_manager.create_access_token(user_data)
                
                await SecurityLogger.log_authentication_event(
                    event_subtype="successful_login",
                    user_id=str(user.id),
                    ip_address=ip_address,
                    success=True
                )
                
                return {
                    'access_token': access_token,
                    'token_type': 'bearer',
                    'expires_in': self.jwt_manager.access_token_expire_minutes * 60,
                    'user': {
                        'id': str(user.id),
                        'username': user.username,
                        'email': user.email,
                        'roles': user.roles,
                        'full_name': user.full_name
                    }
                }
                
        except AuthenticationError:
            raise
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="authentication_system_error",
                user_id=None,
                ip_address=ip_address,
                success=False,
                failure_reason=str(e)
            )
            raise AuthenticationError(
                reason=f"Authentication system error: {str(e)}",
                details={"ip_address": ip_address}
            )
    
    async def validate_token_and_get_user(self, token: str) -> Dict[str, Any]:
        """
        Validate JWT token and return current user information.
        
        Args:
            token: JWT access token
            
        Returns:
            User information and permissions
        """
        # Verify JWT token
        payload = self.jwt_manager.verify_token(token)
        
        # Get current user session from Redis
        session_token = payload.get('session_token')
        if not session_token:
            raise AuthenticationError(
                reason="No session token in JWT payload",
                details={"user_id": payload.get('sub')}
            )
        
        session_data = await session_manager.get_session(session_token)
        
        if not session_data:
            raise AuthenticationError(
                reason="Session expired or invalid",
                details={"session_token_prefix": session_token[:8]}
            )
        
        # Update last activity
        await session_manager.update_session_activity(session_token)
        
        return {
            'user_id': payload['sub'],
            'username': payload['username'],
            'email': payload['email'],
            'roles': payload['roles'],
            'permissions': payload.get('permissions', {}),
            'session_token': session_token
        }
    
    async def logout_user(self, token: str) -> None:
        """
        Logout user by invalidating session.
        
        Args:
            token: JWT access token
        """
        try:
            payload = self.jwt_manager.verify_token(token)
            session_token = payload.get('session_token')
            
            if session_token:
                # Get session data before invalidating for logging
                session_data = await session_manager.get_session(session_token)
                
                # Invalidate session in Redis
                await session_manager.invalidate_session(session_token)
                
                await SecurityLogger.log_authentication_event(
                    event_subtype="user_logout",
                    user_id=payload['sub'],
                    ip_address=session_data.get('ip_address', 'unknown') if session_data else 'unknown',
                    success=True
                )
                        
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="logout_error",
                user_id=None,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            raise AuthenticationError(
                reason=f"Logout failed: {str(e)}",
                details={"token_preview": token[:20] + "..."}
            )
    
    async def logout_all_user_sessions(self, user_id: str) -> int:
        """
        Logout all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        try:
            invalidated_count = await session_manager.invalidate_all_user_sessions(user_id)
            
            await SecurityLogger.log_authentication_event(
                event_subtype="all_sessions_logout",
                user_id=user_id,
                ip_address="unknown",
                success=True,
                details={"sessions_invalidated": invalidated_count}
            )
            
            return invalidated_count
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="all_sessions_logout_error",
                user_id=user_id,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            raise AuthenticationError(
                reason=f"Failed to logout all sessions: {str(e)}",
                details={"user_id": user_id}
            )


# FastAPI Security Dependencies

security = HTTPBearer()
auth_service = AuthenticationService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user.
    
    Returns:
        Current user information and permissions
    """
    try:
        return await auth_service.validate_token_and_get_user(credentials.credentials)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_roles(required_roles: List[str]):
    """
    Create dependency that requires specific roles.
    
    Args:
        required_roles: List of required roles
        
    Returns:
        FastAPI dependency function
    """
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = current_user.get('roles', [])
        
        # Check if user has any of the required roles
        if not any(role in user_roles for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {required_roles}",
            )
        
        return current_user
    
    return role_checker


def require_permissions(required_permissions: List[str]):
    """
    Create dependency that requires specific permissions.
    
    Args:
        required_permissions: List of required permissions
        
    Returns:
        FastAPI dependency function
    """
    def permission_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_permissions = current_user.get('permissions', {})
        
        # Check if user has all required permissions
        missing_permissions = []
        for perm in required_permissions:
            if not user_permissions.get(perm, False):
                missing_permissions.append(perm)
        
        if missing_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {missing_permissions}",
            )
        
        return current_user
    
    return permission_checker


# Global instances
jwt_manager = JWTManager()
password_manager = PasswordManager()
authentication_service = AuthenticationService()