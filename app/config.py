"""
Configuration management for Finsy service.
Loads configuration from environment variables with sensible defaults.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # Flask settings
    FLASK_ENV: str = os.getenv("FLASK_ENV", "development")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    PORT: int = int(os.getenv("PORT", "5000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # Database settings
    FINSY_DB: str = os.getenv("FINSY_DB", "app/db/finsy.db")
    USE_CLOUDANT: bool = os.getenv("USE_CLOUDANT", "False").lower() == "true"
    
    # SQLite settings
    SQLITE_POOL_SIZE: int = int(os.getenv("SQLITE_POOL_SIZE", "5"))
    
    # Cloudant settings
    CLOUDANT_URL: Optional[str] = os.getenv("CLOUDANT_URL")
    CLOUDANT_API_KEY: Optional[str] = os.getenv("CLOUDANT_API_KEY")
    CLOUDANT_DB_NAME: str = os.getenv("CLOUDANT_DB_NAME", "finsy")
    
    # ML Model settings
    RISK_MODEL: str = os.getenv("RISK_MODEL", "app/models/risk_model.pkl")
    
    # Security settings
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    JWT_SECRET_KEY: Optional[str] = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
    
    # Request limits
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH", "16777216"))  # 16MB
    
    # IBM Watson NLU settings
    NLU_API_KEY: Optional[str] = os.getenv("NLU_API_KEY")
    NLU_URL: Optional[str] = os.getenv("NLU_URL")
    NLU_VERSION: str = os.getenv("NLU_VERSION", "2022-04-07")
    
    # IBM watsonx.ai settings
    WATSONX_API_KEY: Optional[str] = os.getenv("WATSONX_API_KEY")
    WATSONX_URL: Optional[str] = os.getenv("WATSONX_URL")
    WATSONX_PROJECT_ID: Optional[str] = os.getenv("WATSONX_PROJECT_ID")
    WATSONX_MODEL_ID: str = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-3-70b-instruct")
    
    # IBM watsonx Orchestrate settings
    ORCHESTRATE_API_KEY: Optional[str] = os.getenv("ORCHESTRATE_API_KEY")
    ORCHESTRATE_URL: Optional[str] = os.getenv("ORCHESTRATE_URL")
    ORCHESTRATE_PROJECT_ID: Optional[str] = os.getenv("ORCHESTRATE_PROJECT_ID")
    
    # IBM Speech-to-Text settings
    STT_API_KEY: Optional[str] = os.getenv("STT_API_KEY")
    STT_URL: Optional[str] = os.getenv("STT_URL")
    
    # IBM Text-to-Speech settings
    TTS_API_KEY: Optional[str] = os.getenv("TTS_API_KEY")
    TTS_URL: Optional[str] = os.getenv("TTS_URL")
    
    # Feature flags
    ENABLE_NLU: bool = os.getenv("ENABLE_NLU", "False").lower() == "true"
    ENABLE_WATSONX: bool = os.getenv("ENABLE_WATSONX", "False").lower() == "true"
    ENABLE_ORCHESTRATE: bool = os.getenv("ENABLE_ORCHESTRATE", "False").lower() == "true"
    ENABLE_SPEECH: bool = os.getenv("ENABLE_SPEECH", "False").lower() == "true"
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "False").lower() == "true"
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Risk scoring constants
    RISK_THRESHOLD_HIGH: float = 0.7
    RISK_THRESHOLD_MEDIUM: float = 0.4
    RISK_THRESHOLD_APPROVAL: float = 0.5
    HIGH_AMOUNT_THRESHOLD: float = 50000.0
    RULE_BASED_WEIGHT: float = 0.4
    MODEL_WEIGHT: float = 0.6
    
    @classmethod
    def validate(cls) -> list:
        """Validate required configuration and return list of missing items"""
        missing = []
        
        if cls.USE_CLOUDANT:
            if not cls.CLOUDANT_URL:
                missing.append("CLOUDANT_URL")
            if not cls.CLOUDANT_API_KEY:
                missing.append("CLOUDANT_API_KEY")
        
        if cls.ENABLE_NLU:
            if not cls.NLU_API_KEY:
                missing.append("NLU_API_KEY")
            if not cls.NLU_URL:
                missing.append("NLU_URL")
        
        if cls.ENABLE_WATSONX:
            if not cls.WATSONX_API_KEY:
                missing.append("WATSONX_API_KEY")
            if not cls.WATSONX_URL:
                missing.append("WATSONX_URL")
            if not cls.WATSONX_PROJECT_ID:
                missing.append("WATSONX_PROJECT_ID")
        
        if cls.ENABLE_ORCHESTRATE:
            if not cls.ORCHESTRATE_API_KEY:
                missing.append("ORCHESTRATE_API_KEY")
            if not cls.ORCHESTRATE_URL:
                missing.append("ORCHESTRATE_URL")
            if not cls.ORCHESTRATE_PROJECT_ID:
                missing.append("ORCHESTRATE_PROJECT_ID")
        
        if cls.ENABLE_SPEECH:
            if not cls.STT_API_KEY:
                missing.append("STT_API_KEY")
            if not cls.STT_URL:
                missing.append("STT_URL")
            if not cls.TTS_API_KEY:
                missing.append("TTS_API_KEY")
            if not cls.TTS_URL:
                missing.append("TTS_URL")
        
        if cls.ENABLE_AUTH and not cls.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        
        return missing


