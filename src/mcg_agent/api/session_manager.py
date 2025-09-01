"""Redis-based session management for Multi-Corpus Governance Agent.

This module implements secure session storage and management using Redis
with TLS encryption and comprehensive security monitoring following
security requirements from docs/security/architecture/security-architecture.md
"""

import json
import ssl
import redis.asyncio as redis
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4

from ..config import settings
from ..utils.exceptions import (
    SecurityValidationError,
    SessionError,
    AuthenticationError
)
from ..utils.logging import SecurityLogger


class RedisSessionManager:
    """
    Secure Redis session management with TLS encryption and monitoring.
    
    Features:
    - TLS encrypted connections
    - Session expiration management
    - Security event logging
    - Session invalidation capabilities
    - Connection pooling for performance
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_pool: Optional[redis.ConnectionPool] = None
        self._setup_tls_context()
    
    def _setup_tls_context(self) -> ssl.SSLContext:
        """Setup TLS context for secure Redis connections."""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE  # Use CERT_REQUIRED in production
        return context
    
    async def initialize(self) -> None:
        """Initialize Redis connection with TLS and connection pooling."""
        try:
            # Create SSL context
            ssl_context = self._setup_tls_context()
            
            # Create connection pool for better performance
            self.connection_pool = redis.ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD.get_secret_value(),
                db=0,  # Use database 0 for sessions
                ssl=True,
                ssl_context=ssl_context,
                max_connections=50,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Create Redis client with connection pool
            self.redis_client = redis.Redis(
                connection_pool=self.connection_pool,
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            
            await SecurityLogger.log_system_event(
                event_type="redis_connection_established",
                success=True,
                details={"host": settings.REDIS_HOST, "port": settings.REDIS_PORT}
            )
            
        except Exception as e:
            await SecurityLogger.log_system_event(
                event_type="redis_connection_failed", 
                success=False,
                details={"error": str(e), "host": settings.REDIS_HOST}
            )
            raise SecurityValidationError(
                validation_type="redis_connection",
                details={"error": str(e), "host": settings.REDIS_HOST}
            )
    
    async def create_session(
        self, 
        user_id: str,
        user_data: Dict[str, Any],
        expires_in: int = 86400  # 24 hours default
    ) -> str:
        """
        Create a new user session in Redis.
        
        Args:
            user_id: User identifier
            user_data: Session data to store
            expires_in: Session expiration time in seconds
            
        Returns:
            Session token/identifier
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            # Generate secure session token
            session_token = str(uuid4())
            session_key = f"session:{session_token}"
            
            # Prepare session data
            session_data = {
                'user_id': user_id,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_activity': datetime.now(timezone.utc).isoformat(),
                'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat(),
                'ip_address': user_data.get('ip_address', 'unknown'),
                'user_agent': user_data.get('user_agent', 'unknown'),
                'username': user_data.get('username', ''),
                'roles': user_data.get('roles', []),
                'permissions': user_data.get('permissions', {}),
                'is_active': True
            }
            
            # Store in Redis with expiration
            await self.redis_client.setex(
                session_key,
                expires_in,
                json.dumps(session_data)
            )
            
            # Track active sessions per user
            user_sessions_key = f"user_sessions:{user_id}"
            await self.redis_client.sadd(user_sessions_key, session_token)
            await self.redis_client.expire(user_sessions_key, expires_in)
            
            await SecurityLogger.log_authentication_event(
                event_subtype="session_created",
                user_id=user_id,
                ip_address=user_data.get('ip_address', 'unknown'),
                success=True,
                details={"session_token_prefix": session_token[:8]}
            )
            
            return session_token
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="session_creation_failed",
                user_id=user_id,
                ip_address=user_data.get('ip_address', 'unknown'),
                success=False,
                failure_reason=str(e)
            )
            raise SessionError(
                reason=f"Failed to create session: {str(e)}",
                details={"user_id": user_id}
            )
    
    async def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data from Redis.
        
        Args:
            session_token: Session identifier
            
        Returns:
            Session data if valid, None if expired/invalid
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            session_key = f"session:{session_token}"
            session_data_str = await self.redis_client.get(session_key)
            
            if not session_data_str:
                return None
            
            session_data = json.loads(session_data_str)
            
            # Check if session is still active
            if not session_data.get('is_active', True):
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            if datetime.now(timezone.utc) > expires_at:
                # Clean up expired session
                await self.invalidate_session(session_token)
                return None
            
            return session_data
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="session_retrieval_error",
                user_id=None,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            raise SessionError(
                reason=f"Failed to retrieve session: {str(e)}",
                details={"session_token_prefix": session_token[:8]}
            )
    
    async def update_session_activity(self, session_token: str) -> bool:
        """
        Update session last activity timestamp.
        
        Args:
            session_token: Session identifier
            
        Returns:
            True if updated successfully, False if session not found
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            session_key = f"session:{session_token}"
            session_data_str = await self.redis_client.get(session_key)
            
            if not session_data_str:
                return False
            
            session_data = json.loads(session_data_str)
            session_data['last_activity'] = datetime.now(timezone.utc).isoformat()
            
            # Get remaining TTL and update
            ttl = await self.redis_client.ttl(session_key)
            if ttl > 0:
                await self.redis_client.setex(
                    session_key,
                    ttl,
                    json.dumps(session_data)
                )
            
            return True
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="session_activity_update_failed",
                user_id=None,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            return False
    
    async def invalidate_session(self, session_token: str) -> bool:
        """
        Invalidate/delete a session from Redis.
        
        Args:
            session_token: Session identifier
            
        Returns:
            True if invalidated successfully
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            session_key = f"session:{session_token}"
            
            # Get session data before deletion for logging
            session_data_str = await self.redis_client.get(session_key)
            user_id = None
            
            if session_data_str:
                session_data = json.loads(session_data_str)
                user_id = session_data.get('user_id')
                
                # Remove from user sessions set
                if user_id:
                    user_sessions_key = f"user_sessions:{user_id}"
                    await self.redis_client.srem(user_sessions_key, session_token)
            
            # Delete session
            result = await self.redis_client.delete(session_key)
            
            if result > 0:
                await SecurityLogger.log_authentication_event(
                    event_subtype="session_invalidated",
                    user_id=user_id,
                    ip_address="unknown",
                    success=True,
                    details={"session_token_prefix": session_token[:8]}
                )
            
            return result > 0
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="session_invalidation_failed",
                user_id=None,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            raise SessionError(
                reason=f"Failed to invalidate session: {str(e)}",
                details={"session_token_prefix": session_token[:8]}
            )
    
    async def invalidate_all_user_sessions(self, user_id: str) -> int:
        """
        Invalidate all sessions for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_tokens = await self.redis_client.smembers(user_sessions_key)
            
            invalidated_count = 0
            
            for session_token in session_tokens:
                if await self.invalidate_session(session_token):
                    invalidated_count += 1
            
            # Clean up the user sessions set
            await self.redis_client.delete(user_sessions_key)
            
            await SecurityLogger.log_authentication_event(
                event_subtype="all_user_sessions_invalidated",
                user_id=user_id,
                ip_address="unknown",
                success=True,
                details={"sessions_invalidated": invalidated_count}
            )
            
            return invalidated_count
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="user_sessions_invalidation_failed",
                user_id=user_id,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            raise SessionError(
                reason=f"Failed to invalidate user sessions: {str(e)}",
                details={"user_id": user_id}
            )
    
    async def get_active_sessions_count(self, user_id: str) -> int:
        """
        Get count of active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of active sessions
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            user_sessions_key = f"user_sessions:{user_id}"
            session_tokens = await self.redis_client.smembers(user_sessions_key)
            
            active_count = 0
            for session_token in session_tokens:
                session_data = await self.get_session(session_token)
                if session_data:
                    active_count += 1
            
            return active_count
            
        except Exception as e:
            await SecurityLogger.log_system_event(
                event_type="session_count_error",
                success=False,
                details={"user_id": user_id, "error": str(e)}
            )
            return 0
    
    async def extend_session(
        self, 
        session_token: str, 
        extend_by_seconds: int = 3600
    ) -> bool:
        """
        Extend session expiration time.
        
        Args:
            session_token: Session identifier
            extend_by_seconds: Seconds to extend by (default 1 hour)
            
        Returns:
            True if extended successfully
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            session_key = f"session:{session_token}"
            
            # Get current session data
            session_data_str = await self.redis_client.get(session_key)
            if not session_data_str:
                return False
            
            session_data = json.loads(session_data_str)
            
            # Update expiration
            current_expires = datetime.fromisoformat(session_data['expires_at'])
            new_expires = current_expires + timedelta(seconds=extend_by_seconds)
            session_data['expires_at'] = new_expires.isoformat()
            
            # Update in Redis with new TTL
            current_ttl = await self.redis_client.ttl(session_key)
            new_ttl = current_ttl + extend_by_seconds
            
            await self.redis_client.setex(
                session_key,
                new_ttl,
                json.dumps(session_data)
            )
            
            await SecurityLogger.log_authentication_event(
                event_subtype="session_extended",
                user_id=session_data.get('user_id'),
                ip_address=session_data.get('ip_address', 'unknown'),
                success=True,
                details={
                    "session_token_prefix": session_token[:8],
                    "extended_by_seconds": extend_by_seconds
                }
            )
            
            return True
            
        except Exception as e:
            await SecurityLogger.log_authentication_event(
                event_subtype="session_extension_failed",
                user_id=None,
                ip_address="unknown",
                success=False,
                failure_reason=str(e)
            )
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions (maintenance function).
        
        Returns:
            Number of sessions cleaned up
        """
        if not self.redis_client:
            await self.initialize()
        
        try:
            # This is handled automatically by Redis TTL, but we can
            # clean up orphaned user session sets
            cleanup_count = 0
            
            # Get all user session keys
            user_session_keys = []
            async for key in self.redis_client.scan_iter(match="user_sessions:*"):
                user_session_keys.append(key)
            
            for user_sessions_key in user_session_keys:
                session_tokens = await self.redis_client.smembers(user_sessions_key)
                valid_tokens = []
                
                for session_token in session_tokens:
                    session_data = await self.get_session(session_token)
                    if session_data:
                        valid_tokens.append(session_token)
                    else:
                        cleanup_count += 1
                
                # Update the set with only valid tokens
                if valid_tokens:
                    await self.redis_client.delete(user_sessions_key)
                    await self.redis_client.sadd(user_sessions_key, *valid_tokens)
                else:
                    await self.redis_client.delete(user_sessions_key)
            
            await SecurityLogger.log_system_event(
                event_type="session_cleanup_completed",
                success=True,
                details={"cleaned_up_count": cleanup_count}
            )
            
            return cleanup_count
            
        except Exception as e:
            await SecurityLogger.log_system_event(
                event_type="session_cleanup_failed",
                success=False,
                details={"error": str(e)}
            )
            return 0
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform Redis connection health check.
        
        Returns:
            Health check status and metrics
        """
        if not self.redis_client:
            return {
                "status": "unhealthy",
                "error": "Redis client not initialized"
            }
        
        try:
            # Test basic connectivity
            start_time = datetime.now(timezone.utc)
            await self.redis_client.ping()
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Get Redis info
            redis_info = await self.redis_client.info()
            
            return {
                "status": "healthy",
                "response_time_seconds": response_time,
                "connected_clients": redis_info.get('connected_clients', 0),
                "used_memory_human": redis_info.get('used_memory_human', 'unknown'),
                "redis_version": redis_info.get('redis_version', 'unknown')
            }
            
        except Exception as e:
            return {
                "status": "unhealthy", 
                "error": str(e)
            }
    
    async def close(self) -> None:
        """Close Redis connections gracefully."""
        if self.redis_client:
            await self.redis_client.close()
        
        if self.connection_pool:
            await self.connection_pool.disconnect()


# Global session manager instance
session_manager = RedisSessionManager()