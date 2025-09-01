"""Database session management for Multi-Corpus Governance Agent.

This module provides secure database connection management, session handling,
and connection pooling following security requirements from:
docs/security/architecture/security-architecture.md
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any
from urllib.parse import urlparse
import ssl

from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, DisconnectionError

from ..config import settings
from ..utils.exceptions import DatabaseConnectionError, SecurityValidationError
from ..utils.logging import SecurityLogger


class DatabaseManager:
    """
    Secure database connection manager with connection pooling,
    encryption enforcement, and security monitoring.
    """
    
    def __init__(self):
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_engine = None
        self._async_session_factory: Optional[async_sessionmaker] = None
        self._sync_session_factory = None
        self._connection_validated = False
        self._security_checks_passed = False
        
    async def initialize(self) -> None:
        """Initialize database connections with security validation."""
        try:
            # Validate connection string security
            await self._validate_connection_security()
            
            # Create async engine with security configuration
            self._async_engine = create_async_engine(
                self._get_async_database_url(),
                **self._get_engine_config()
            )
            
            # Create sync engine for migrations and admin tasks
            self._sync_engine = create_engine(
                self._get_sync_database_url(),
                **self._get_engine_config()
            )
            
            # Create session factories
            self._async_session_factory = async_sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                class_=Session,
                expire_on_commit=False,
                autoflush=True,
                autocommit=False
            )
            
            # Test connections
            await self._test_connections()
            
            # Setup connection event handlers for security monitoring
            self._setup_security_monitoring()
            
            self._connection_validated = True
            
            await SecurityLogger.log_database_initialization(
                database_type="postgresql",
                security_validated=True,
                encryption_enabled=True
            )
            
        except Exception as e:
            await SecurityLogger.log_database_error(
                error_type="initialization_failed",
                error_message=str(e),
                database_type="postgresql"
            )
            raise DatabaseConnectionError(
                database_type="postgresql",
                reason=f"Database initialization failed: {str(e)}",
                details={"connection_validated": self._connection_validated}
            )
    
    def _get_async_database_url(self) -> str:
        """Get async database URL with security parameters."""
        # Convert sync URL to async URL
        sync_url = settings.postgres_url
        if sync_url.startswith('postgresql://'):
            return sync_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
        elif sync_url.startswith('postgresql+psycopg2://'):
            return sync_url.replace('postgresql+psycopg2://', 'postgresql+asyncpg://', 1)
        else:
            return f"postgresql+asyncpg://{sync_url}"
    
    def _get_sync_database_url(self) -> str:
        """Get sync database URL with security parameters."""
        return str(settings.postgres_url)
    
    def _get_engine_config(self) -> Dict[str, Any]:
        """Get engine configuration with security and performance settings."""
        return {
            # Connection pooling for performance and security
            'poolclass': QueuePool,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
            'pool_recycle': 3600,  # Recycle connections every hour
            'pool_pre_ping': True,  # Validate connections before use
            
            # Security settings
            'connect_args': {
                'sslmode': 'require',  # Require TLS encryption
                'sslcert': None,  # Client certificate if needed
                'sslkey': None,   # Client key if needed
                'sslrootcert': None,  # CA certificate if needed
                'application_name': 'mcg-agent',
                'connect_timeout': 10,
            },
            
            # Logging and monitoring
            'echo': False,  # Set to True for SQL debugging (dev only)
            'echo_pool': False,  # Pool debugging
            
            # Performance tuning
            'execution_options': {
                'isolation_level': 'READ_COMMITTED',
                'autocommit': False
            }
        }
    
    async def _validate_connection_security(self) -> None:
        """Validate database connection meets security requirements."""
        db_url = str(settings.postgres_url)
        parsed = urlparse(db_url)
        
        security_issues = []
        
        # Check for required TLS/SSL
        if 'sslmode' not in db_url and 'localhost' not in parsed.hostname:
            security_issues.append("TLS/SSL not enforced for non-localhost connection")
        
        # Check for weak passwords (basic check)
        if parsed.password and len(parsed.password) < 16:
            security_issues.append("Database password appears to be weak (< 16 characters)")
        
        # Check for default credentials
        if parsed.username in ['postgres', 'admin', 'root'] and parsed.password in ['password', '123456', 'admin']:
            security_issues.append("Default or weak credentials detected")
        
        # Check for production database naming
        if parsed.path in ['/test', '/dev', '/development'] and settings.environment == 'production':
            security_issues.append("Non-production database name in production environment")
        
        if security_issues:
            await SecurityLogger.log_security_validation_error(
                validation_type="database_connection_security",
                issues=security_issues
            )
            raise SecurityValidationError(
                validation_type="database_connection_security",
                details={"issues": security_issues}
            )
        
        self._security_checks_passed = True
    
    async def _test_connections(self) -> None:
        """Test database connections and validate functionality."""
        # Test async connection
        try:
            async with self._async_engine.begin() as conn:
                result = await conn.execute("SELECT 1 as test")
                test_value = result.scalar()
                if test_value != 1:
                    raise DatabaseConnectionError(
                        database_type="postgresql",
                        reason="Async connection test failed"
                    )
        except Exception as e:
            raise DatabaseConnectionError(
                database_type="postgresql", 
                reason=f"Async connection test failed: {str(e)}"
            )
        
        # Test sync connection
        try:
            with self._sync_engine.begin() as conn:
                result = conn.execute("SELECT 1 as test")
                test_value = result.scalar()
                if test_value != 1:
                    raise DatabaseConnectionError(
                        database_type="postgresql",
                        reason="Sync connection test failed"
                    )
        except Exception as e:
            raise DatabaseConnectionError(
                database_type="postgresql",
                reason=f"Sync connection test failed: {str(e)}"
            )
    
    def _setup_security_monitoring(self) -> None:
        """Setup database connection security monitoring."""
        
        @event.listens_for(self._async_engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Monitor database connections for security."""
            asyncio.create_task(SecurityLogger.log_database_connection(
                event="connection_established",
                connection_id=id(dbapi_connection),
                security_validated=self._security_checks_passed
            ))
        
        @event.listens_for(self._async_engine.sync_engine, "disconnect")
        def on_disconnect(dbapi_connection, connection_record):
            """Monitor database disconnections."""
            asyncio.create_task(SecurityLogger.log_database_connection(
                event="connection_closed",
                connection_id=id(dbapi_connection)
            ))
        
        @event.listens_for(self._async_engine.sync_engine, "handle_error")
        def on_error(exception_context):
            """Monitor database errors for security incidents."""
            if isinstance(exception_context.original_exception, DisconnectionError):
                asyncio.create_task(SecurityLogger.log_database_error(
                    error_type="connection_lost",
                    error_message=str(exception_context.original_exception),
                    database_type="postgresql"
                ))
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get async database session with automatic cleanup and error handling.
        
        Usage:
            async with db_manager.get_session() as session:
                # Use session for database operations
                result = await session.execute(query)
                await session.commit()
        """
        if not self._connection_validated:
            raise DatabaseConnectionError(
                database_type="postgresql",
                reason="Database not initialized. Call initialize() first."
            )
        
        session = self._async_session_factory()
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            await SecurityLogger.log_database_error(
                error_type="session_error",
                error_message=str(e),
                database_type="postgresql"
            )
            raise DatabaseConnectionError(
                database_type="postgresql",
                reason=f"Database session error: {str(e)}"
            )
        except Exception as e:
            await session.rollback()
            await SecurityLogger.log_database_error(
                error_type="unexpected_session_error",
                error_message=str(e),
                database_type="postgresql"
            )
            raise
        finally:
            await session.close()
    
    def get_sync_session(self) -> Session:
        """
        Get sync database session for migrations and admin operations.
        
        Returns a session that must be manually closed.
        """
        if not self._connection_validated:
            raise DatabaseConnectionError(
                database_type="postgresql",
                reason="Database not initialized. Call initialize() first."
            )
        
        return self._sync_session_factory()
    
    async def execute_raw_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute raw SQL with security validation and logging.
        
        Args:
            sql: SQL query to execute
            params: Query parameters
            
        Returns:
            Query result
        """
        # Basic SQL injection prevention
        if self._contains_suspicious_sql(sql):
            await SecurityLogger.log_security_violation(
                violation_type="suspicious_sql_detected",
                details={"sql_preview": sql[:100], "params": params}
            )
            raise SecurityValidationError(
                validation_type="sql_injection_prevention",
                details={"sql_preview": sql[:100]}
            )
        
        async with self.get_session() as session:
            try:
                if params:
                    result = await session.execute(sql, params)
                else:
                    result = await session.execute(sql)
                await session.commit()
                return result
            except Exception as e:
                await SecurityLogger.log_database_error(
                    error_type="raw_sql_execution_failed",
                    error_message=str(e),
                    database_type="postgresql"
                )
                raise
    
    def _contains_suspicious_sql(self, sql: str) -> bool:
        """Basic SQL injection detection."""
        sql_lower = sql.lower()
        
        # Check for suspicious patterns
        suspicious_patterns = [
            'drop table', 'drop database', 'delete from',
            'truncate', 'alter table', 'create user',
            'grant all', 'revoke', '1=1', '1 or 1',
            'union select', 'information_schema',
            'pg_user', 'pg_shadow'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in sql_lower:
                return True
        
        # Check for multiple statements (basic)
        if ';' in sql and not sql.strip().endswith(';'):
            return True
        
        return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check for monitoring.
        
        Returns:
            Health status and metrics
        """
        try:
            start_time = asyncio.get_event_loop().time()
            
            async with self.get_session() as session:
                # Test basic query
                result = await session.execute("SELECT 1 as health_check")
                health_value = result.scalar()
                
                # Test connection pool status
                pool = self._async_engine.pool
                pool_status = {
                    'size': pool.size(),
                    'checked_in': pool.checkedin(),
                    'checked_out': pool.checkedout(),
                    'overflow': pool.overflow(),
                    'invalid': pool.invalid()
                }
            
            response_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            health_status = {
                'status': 'healthy' if health_value == 1 else 'unhealthy',
                'response_time_ms': response_time,
                'connection_pool': pool_status,
                'security_validated': self._security_checks_passed,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            await SecurityLogger.log_database_health_check(
                status=health_status['status'],
                response_time_ms=response_time,
                pool_status=pool_status
            )
            
            return health_status
            
        except Exception as e:
            error_status = {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }
            
            await SecurityLogger.log_database_error(
                error_type="health_check_failed",
                error_message=str(e),
                database_type="postgresql"
            )
            
            return error_status
    
    async def close(self) -> None:
        """Close database connections and cleanup resources."""
        try:
            if self._async_engine:
                await self._async_engine.dispose()
            
            if self._sync_engine:
                self._sync_engine.dispose()
            
            await SecurityLogger.log_database_connection(
                event="connections_closed",
                cleanup_completed=True
            )
            
        except Exception as e:
            await SecurityLogger.log_database_error(
                error_type="cleanup_failed",
                error_message=str(e),
                database_type="postgresql"
            )
            raise


# Global database manager instance
db_manager = DatabaseManager()