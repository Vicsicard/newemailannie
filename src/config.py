"""
Configuration settings for the AI Email Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # Email Configuration
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "gmail")
    EMAIL_ADDRESS: str = os.getenv("EMAIL_ADDRESS", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    IMAP_SERVER: str = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT: int = int(os.getenv("IMAP_PORT", "993"))
    
    # Salesforce Configuration
    SALESFORCE_USERNAME: str = os.getenv("SALESFORCE_USERNAME", "")
    SALESFORCE_PASSWORD: str = os.getenv("SALESFORCE_PASSWORD", "")
    SALESFORCE_SECURITY_TOKEN: str = os.getenv("SALESFORCE_SECURITY_TOKEN", "")
    SALESFORCE_DOMAIN: str = os.getenv("SALESFORCE_DOMAIN", "login")
    
    # AI Configuration
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openai")
    
    # Email Sending Configuration
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    
    # Application Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    CHECK_INTERVAL_MINUTES: int = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))
    MAX_EMAILS_PER_BATCH: int = int(os.getenv("MAX_EMAILS_PER_BATCH", "50"))
    
    # Classification confidence thresholds
    CLASSIFICATION_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Email templates directory
    TEMPLATES_DIR: str = "templates"
    
    class Config:
        env_file = ".env"

# Global settings instance
settings = Settings()

# Validation
def validate_settings():
    """Validate required settings"""
    required_fields = [
        "EMAIL_ADDRESS",
        "EMAIL_PASSWORD",
        "SALESFORCE_USERNAME",
        "SALESFORCE_PASSWORD",
        "SALESFORCE_SECURITY_TOKEN"
    ]
    
    missing_fields = []
    for field in required_fields:
        if not getattr(settings, field):
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_fields)}")
    
    # Validate AI provider has API key
    if settings.AI_PROVIDER == "openai" and not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required when using OpenAI")
    elif settings.AI_PROVIDER == "anthropic" and not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic")

if __name__ == "__main__":
    validate_settings()
    print("Configuration validated successfully!")
