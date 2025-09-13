"""
Configuration management for the Multi-Corpus Governance Agent.

This module handles all configuration from environment variables,
with validation and type conversion using Pydantic Settings.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus

from pydantic import Field, validator, root_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    # PostgreSQL settings
    POSTGRES_USER: str = Field(default="mcg_agent", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(default="password", description="PostgreSQL password")
    POSTGRES_DB: str = Field(default="mcg_agent", description="PostgreSQL database name")
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    
    # Database URL (can be set directly or constructed from above)
    DATABASE_URL: Optional[str] = Field(default=None, description="Complete database URL")
    TEST_DATABASE_URL: str = Field(
        default="sqlite:///./test_mcg_agent.db",
        description="Test database URL"
    )
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL URL from components"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # URL-encode password to handle special characters
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


class RedisSettings(BaseSettings):
    """Redis configuration settings"""
    
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: Optional[str] = Field(default=None, description="Redis password")
    REDIS_TLS: bool = Field(default=False, description="Use TLS for Redis connection")
    REDIS_URL: Optional[str] = Field(default=None, description="Complete Redis URL")
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components"""
        if self.REDIS_URL:
            return self.REDIS_URL
        
        scheme = "rediss" if self.REDIS_TLS else "redis"
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(
        default="your-jwt-secret-key-change-this-in-production",
        description="JWT secret key for token signing"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="JWT token expiration time in minutes"
    )
    
    # Encryption
    ENCRYPTION_KEY: str = Field(
        default="your-32-byte-encryption-key-change-this-in-production",
        description="Encryption key for sensitive data"
    )
    
    @validator('JWT_SECRET_KEY')
    def validate_jwt_secret(cls, v):
        if v == "your-jwt-secret-key-change-this-in-production":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT_SECRET_KEY must be changed in production")
        return v
    
    @validator('ENCRYPTION_KEY')
    def validate_encryption_key(cls, v):
        if v == "your-32-byte-encryption-key-change-this-in-production":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("ENCRYPTION_KEY must be changed in production")
        return v


class APISettings(BaseSettings):
    """API keys and external service configuration"""
    
    # AI Service API Keys
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    COHERE_API_KEY: Optional[str] = Field(default=None, description="Cohere API key")
    HUGGINGFACE_API_KEY: Optional[str] = Field(default=None, description="Hugging Face API key")
    # Dev generation model (OpenAI)
    OPENAI_MODEL: Optional[str] = Field(default="gpt-4o-mini", description="OpenAI model name for dev provider")
    
    @validator('OPENAI_API_KEY', 'ANTHROPIC_API_KEY')
    def validate_required_api_keys(cls, v, field):
        if not v and os.getenv("ENVIRONMENT") == "production":
            raise ValueError(f"{field.name} is required in production")
        return v


class ServerSettings(BaseSettings):
    """Server configuration settings"""
    
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")
    ENVIRONMENT: str = Field(default="development", description="Environment mode")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    
    # Worker configuration
    WORKERS: int = Field(default=4, description="Number of worker processes")
    WORKER_CLASS: str = Field(
        default="uvicorn.workers.UvicornWorker",
        description="Worker class for production"
    )
    
    @validator('ENVIRONMENT')
    def validate_environment(cls, v):
        valid_envs = ['development', 'production', 'test']
        if v not in valid_envs:
            raise ValueError(f"ENVIRONMENT must be one of: {valid_envs}")
        return v
    
    @validator('LOG_LEVEL')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()


class GovernanceSettings(BaseSettings):
    """Governance and agent configuration settings"""
    
    # API Call Limits per agent per task
    IDEATOR_MAX_API_CALLS: int = Field(default=2, description="Max API calls for Ideator agent")
    DRAFTER_MAX_API_CALLS: int = Field(default=1, description="Max API calls for Drafter agent")
    CRITIC_MAX_API_CALLS: int = Field(default=2, description="Max API calls for Critic agent")
    REVISOR_MAX_API_CALLS: int = Field(default=1, description="Max API calls for Revisor agent")
    SUMMARIZER_MAX_API_CALLS: int = Field(default=0, description="Max API calls for Summarizer agent")
    
    # MVLM Configuration
    MVLM_ENABLED: bool = Field(default=True, description="Enable MVLM usage")
    MVLM_FALLBACK_ENABLED: bool = Field(default=True, description="Enable MVLM fallback to API")
    MVLM_MODEL_PATH: Optional[str] = Field(default=None, description="Path to local MVLM model")
    
    # Scoring Thresholds
    COVERAGE_SCORE_MIN: float = Field(default=0.7, description="Minimum coverage score")
    TONE_SCORE_MIN: float = Field(default=0.6, description="Minimum tone score")
    DIVERSITY_CHECK_ENABLED: bool = Field(default=True, description="Enable diversity checking")
    
    @validator('COVERAGE_SCORE_MIN', 'TONE_SCORE_MIN')
    def validate_score_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Score thresholds must be between 0.0 and 1.0")
        return v


class CorpusSettings(BaseSettings):
    """Corpus configuration settings"""
    
    # Personal Corpus
    PERSONAL_CORPUS_ENABLED: bool = Field(default=True, description="Enable personal corpus")
    PERSONAL_MAX_RESULTS: int = Field(default=20, description="Max results from personal corpus")
    PERSONAL_SNIPPET_LENGTH: int = Field(default=240, description="Personal snippet length")
    
    # Social Corpus
    SOCIAL_CORPUS_ENABLED: bool = Field(default=True, description="Enable social corpus")
    SOCIAL_MAX_RESULTS: int = Field(default=30, description="Max results from social corpus")
    SOCIAL_SNIPPET_LENGTH: int = Field(default=150, description="Social snippet length")
    
    # Published Corpus
    PUBLISHED_CORPUS_ENABLED: bool = Field(default=True, description="Enable published corpus")
    PUBLISHED_MAX_RESULTS: int = Field(default=20, description="Max results from published corpus")
    PUBLISHED_SNIPPET_LENGTH: int = Field(default=200, description="Published snippet length")
    
    # RAG Settings
    RAG_ENABLED: bool = Field(default=True, description="Enable RAG functionality")
    RAG_MAX_RESULTS: int = Field(default=10, description="Max RAG results")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.8, description="RAG similarity threshold")
    
    @validator('RAG_SIMILARITY_THRESHOLD')
    def validate_similarity_threshold(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("RAG_SIMILARITY_THRESHOLD must be between 0.0 and 1.0")
        return v


class CacheSettings(BaseSettings):
    """Caching configuration settings"""
    
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL: int = Field(default=3600, description="Cache TTL in seconds")
    CACHE_MAX_SIZE: int = Field(default=1000, description="Maximum cache size")
    
    # Search caching
    SEARCH_CACHE_ENABLED: bool = Field(default=True, description="Enable search result caching")
    SEARCH_CACHE_TTL: int = Field(default=1800, description="Search cache TTL in seconds")


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings"""
    
    # Sentry
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    SENTRY_ENVIRONMENT: Optional[str] = Field(default=None, description="Sentry environment")
    
    # Metrics
    METRICS_ENABLED: bool = Field(default=False, description="Enable Prometheus metrics")
    METRICS_PORT: int = Field(default=9090, description="Metrics server port")
    
    # Health checks
    HEALTH_CHECK_ENABLED: bool = Field(default=True, description="Enable health checks")
    HEALTH_CHECK_TIMEOUT: int = Field(default=10, description="Health check timeout")


class ProductionSettings(BaseSettings):
    """Production-specific settings"""
    
    # Security
    PROD_FORCE_HTTPS: bool = Field(default=True, description="Force HTTPS in production")
    PROD_SECURE_COOKIES: bool = Field(default=True, description="Use secure cookies")
    PROD_CORS_ORIGINS: str = Field(
        default="",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # SSL/TLS
    SSL_KEYFILE: Optional[str] = Field(default=None, description="SSL private key file")
    SSL_CERTFILE: Optional[str] = Field(default=None, description="SSL certificate file")
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=60,
        description="Rate limit requests per minute"
    )
    RATE_LIMIT_BURST: int = Field(default=10, description="Rate limit burst size")
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        if not self.PROD_CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.PROD_CORS_ORIGINS.split(',') if origin.strip()]


class FeatureFlags(BaseSettings):
    """Feature flag settings for experimental features"""
    
    FEATURE_VOICE_FINGERPRINTING: bool = Field(
        default=True,
        description="Enable voice fingerprinting feature"
    )
    FEATURE_ADVANCED_RAG: bool = Field(
        default=False,
        description="Enable advanced RAG features"
    )
    FEATURE_MULTI_LANGUAGE: bool = Field(
        default=False,
        description="Enable multi-language support"
    )
    FEATURE_REAL_TIME_PROCESSING: bool = Field(
        default=False,
        description="Enable real-time processing"
    )
    FEATURE_RESPONSE_OPTIMIZER: bool = Field(
        default=False,
        description="Enable response optimizer in Revisor/Summarizer",
    )

class OptimizationSettings(BaseSettings):
    """Response optimizer configuration"""
    STRATEGY: str = Field(default="balanced", description="speed|quality|balanced|adaptive")
    TIMEBOX_MS: int = Field(default=1500, description="Per-operation timebox in ms")
    ENABLE_CACHE: bool = Field(default=True, description="Enable optimizer TTL cache")
    CACHE_TTL_MS: int = Field(default=60000, description="Optimizer cache TTL in ms")
    QA_MIN_TONE: float = Field(default=0.5, description="Minimum tone score for QA")
    QA_MIN_STYLE: float = Field(default=0.5, description="Minimum style score for QA")
    QA_MIN_OVERALL: float = Field(default=0.6, description="Minimum overall QA score")
    QA_ENFORCE: bool = Field(default=False, description="Enforce QA gating in quality strategy")


class Settings(BaseSettings):
    """Main settings class that combines all configuration sections"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # Include all setting sections
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    api: APISettings = Field(default_factory=APISettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    governance: GovernanceSettings = Field(default_factory=GovernanceSettings)
    corpus: CorpusSettings = Field(default_factory=CorpusSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    production: ProductionSettings = Field(default_factory=ProductionSettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    optimization: OptimizationSettings = Field(default_factory=OptimizationSettings)
    
    # Simple top-level settings used by various modules
    AUDIT_TRAIL_PATH: str = Field(
        default="./audit",
        description="Filesystem directory for immutable audit trail logs",
    )
    MVLM_GPT2_MODEL_PATH: str = Field(
        default="./models/mvlm_gpt2",
        description="Filesystem path to MVLM-GPT2 model (optional)",
    )
    SIMONE_ENHANCED_MODEL_PATH: str = Field(
        default="./models/simone_enhanced",
        description="Filesystem path to Enhanced SIM-ONE model (optional)",
    )
    # Generation provider selector: openai | mvlm | punctuation_only
    GEN_PROVIDER: str = Field(default="punctuation_only", description="Generation provider selector")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize subsections with environment variables
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.security = SecuritySettings()
        self.api = APISettings()
        self.server = ServerSettings()
        self.governance = GovernanceSettings()
        self.corpus = CorpusSettings()
        self.cache = CacheSettings()
        self.monitoring = MonitoringSettings()
        self.production = ProductionSettings()
        self.features = FeatureFlags()
        self.optimization = OptimizationSettings()
    
    # Convenience properties for backward compatibility
    @property
    def postgres_url(self) -> str:
        return self.database.postgres_url
    
    @property
    def redis_url(self) -> str:
        return self.redis.redis_url
    
    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.security.JWT_SECRET_KEY
    
    @property
    def POSTGRES_HOST(self) -> str:
        return self.database.POSTGRES_HOST
    
    @property
    def POSTGRES_PORT(self) -> int:
        return self.database.POSTGRES_PORT
    
    @property
    def REDIS_HOST(self) -> str:
        return self.redis.REDIS_HOST
    
    @property
    def REDIS_PORT(self) -> int:
        return self.redis.REDIS_PORT
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.server.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.server.ENVIRONMENT == "development"
    
    def is_testing(self) -> bool:
        """Check if running in test environment"""
        return self.server.ENVIRONMENT == "test"
    
    def get_database_url(self, for_testing: bool = False) -> str:
        """Get the appropriate database URL"""
        if for_testing:
            return self.database.TEST_DATABASE_URL
        return self.database.postgres_url
    
    def validate_production_config(self) -> List[str]:
        """Validate configuration for production deployment"""
        issues = []
        
        if not self.is_production():
            return issues
        
        # Check security settings
        if self.security.JWT_SECRET_KEY == "your-jwt-secret-key-change-this-in-production":
            issues.append("JWT_SECRET_KEY must be changed in production")
        
        if self.security.ENCRYPTION_KEY == "your-32-byte-encryption-key-change-this-in-production":
            issues.append("ENCRYPTION_KEY must be changed in production")
        
        # Check API keys
        if not self.api.OPENAI_API_KEY and not self.api.ANTHROPIC_API_KEY:
            issues.append("At least one AI service API key is required")
        
        # Check database configuration
        if "sqlite" in self.database.postgres_url.lower():
            issues.append("SQLite should not be used in production")
        
        return issues


# Global settings instance
settings = Settings()


# Utility functions
def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment"""
    global settings
    settings = Settings()
    return settings


def validate_environment() -> Dict[str, Any]:
    """Validate the current environment configuration"""
    validation_result = {
        'valid': True,
        'environment': settings.server.ENVIRONMENT,
        'issues': [],
        'warnings': []
    }
    
    # Production validation
    if settings.is_production():
        prod_issues = settings.validate_production_config()
        validation_result['issues'].extend(prod_issues)
        if prod_issues:
            validation_result['valid'] = False
    
    # General validation
    try:
        # Test database URL construction
        db_url = settings.get_database_url()
        if not db_url:
            validation_result['issues'].append("DATABASE_URL is not configured")
            validation_result['valid'] = False
    except Exception as e:
        validation_result['issues'].append(f"Database configuration error: {e}")
        validation_result['valid'] = False
    
    try:
        # Test Redis URL construction
        redis_url = settings.redis_url
        if not redis_url:
            validation_result['warnings'].append("REDIS_URL is not configured")
    except Exception as e:
        validation_result['warnings'].append(f"Redis configuration warning: {e}")
    
    return validation_result
