"""
Environment Configuration for LIMS.Pro
Supports dev, staging, and production environments
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from enum import Enum


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings with environment-based configuration.
    All sensitive values come from environment variables.
    """
    
    # Environment
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    DEBUG: bool = Field(default=True)
    
    # Application
    APP_NAME: str = Field(default="LIMS.Pro")
    APP_VERSION: str = Field(default="1.0.0")
    API_PREFIX: str = Field(default="/api")
    
    # MongoDB
    MONGO_URL: str = Field(...)
    DB_NAME: str = Field(default="test_database")
    MONGO_MIN_POOL_SIZE: int = Field(default=1)
    MONGO_MAX_POOL_SIZE: int = Field(default=10)
    MONGO_CONNECT_TIMEOUT_MS: int = Field(default=5000)
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = Field(default=5000)
    
    # JWT
    JWT_SECRET: str = Field(default="dev-secret-change-in-production")
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_HOURS: int = Field(default=24)
    
    # CORS
    CORS_ORIGINS: str = Field(default="*")
    
    # SendGrid (optional)
    SENDGRID_API_KEY: Optional[str] = Field(default=None)
    SENDGRID_FROM_EMAIL: Optional[str] = Field(default=None)
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100)
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v):
        if isinstance(v, str):
            v = v.lower()
            if v in ["dev", "development"]:
                return Environment.DEVELOPMENT
            elif v in ["staging", "stage"]:
                return Environment.STAGING
            elif v in ["prod", "production"]:
                return Environment.PRODUCTION
        return v
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT
    
    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == Environment.STAGING
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @property
    def mongodb_options(self) -> dict:
        """Get MongoDB connection options based on environment"""
        options = {
            "minPoolSize": self.MONGO_MIN_POOL_SIZE,
            "maxPoolSize": self.MONGO_MAX_POOL_SIZE,
            "connectTimeoutMS": self.MONGO_CONNECT_TIMEOUT_MS,
            "serverSelectionTimeoutMS": self.MONGO_SERVER_SELECTION_TIMEOUT_MS,
        }
        
        # Production-specific hardening
        if self.is_production:
            options.update({
                "retryWrites": True,
                "w": "majority",
                "journal": True,
                "maxPoolSize": 50,
                "minPoolSize": 5,
            })
        
        return options
    
    def validate_production_config(self):
        """Validate that production has proper security settings"""
        errors = []
        
        if self.is_production:
            if self.JWT_SECRET == "dev-secret-change-in-production":
                errors.append("JWT_SECRET must be changed for production")
            
            if len(self.JWT_SECRET) < 32:
                errors.append("JWT_SECRET should be at least 32 characters in production")
            
            if self.CORS_ORIGINS == "*":
                errors.append("CORS_ORIGINS should not be '*' in production")
            
            if self.DEBUG:
                errors.append("DEBUG should be False in production")
        
        return errors


class DevelopmentSettings(Settings):
    """Development environment defaults"""
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    CORS_ORIGINS: str = "*"


class StagingSettings(Settings):
    """Staging environment defaults"""
    ENVIRONMENT: Environment = Environment.STAGING
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    MONGO_MAX_POOL_SIZE: int = 20


class ProductionSettings(Settings):
    """Production environment defaults"""
    ENVIRONMENT: Environment = Environment.PRODUCTION
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"
    MONGO_MAX_POOL_SIZE: int = 50
    MONGO_MIN_POOL_SIZE: int = 5


@lru_cache()
def get_settings() -> Settings:
    """
    Get settings instance based on ENVIRONMENT variable.
    Cached for performance.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    
    if env in ["prod", "production"]:
        return ProductionSettings()
    elif env in ["staging", "stage"]:
        return StagingSettings()
    else:
        return DevelopmentSettings()


def get_safe_config_for_logging(settings: Settings) -> dict:
    """
    Get configuration dict safe for logging (no secrets)
    """
    return {
        "environment": settings.ENVIRONMENT.value,
        "debug": settings.DEBUG,
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "db_name": settings.DB_NAME,
        "log_level": settings.LOG_LEVEL,
        "cors_origins": settings.cors_origins_list,
        "jwt_expiration_hours": settings.JWT_EXPIRATION_HOURS,
        "mongo_pool_size": f"{settings.MONGO_MIN_POOL_SIZE}-{settings.MONGO_MAX_POOL_SIZE}",
        "sendgrid_configured": settings.SENDGRID_API_KEY is not None,
    }
