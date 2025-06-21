from pydantic_settings import BaseSettings
from typing import Optional
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "Wedy Web API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # DB URL
    DATABASE_URL: str
    
    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: str
    SMTP_HOST: str
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # SMS
    ESKIZ_EMAIL: str
    ESKIZ_PASSWORD: str

    # AWS S3
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "eu-north-1"
    S3_BUCKET_NAME: str
    S3_ENDPOINT_URL: Optional[str] = None

    # Payme Payment Gateway
    PAYME_MERCHANT_ID: str
    PAYME_SECRET_KEY: str
    PAYME_TEST_MODE: bool = True
    PAYME_CALLBACK_URL: str = "https://api.wedy.uz/payme/webhook"
    PAYME_API_URL: str = "https://checkout.paycom.uz"
    PAYME_TEST_API_URL: str = "https://test.paycom.uz"
    

    # Admin Configuration
    DEFAULT_ADMIN_EMAIL: str
    DEFAULT_ADMIN_PASSWORD: str
    DEFAULT_ADMIN_FIRSTNAME: str
    DEFAULT_ADMIN_LASTNAME: str
    
    # Default Admin
    DEFAULT_ADMIN_EMAIL: str = "admin@wedy.uz"
    DEFAULT_ADMIN_PASSWORD: str = "Admin123!"
    DEFAULT_ADMIN_FIRSTNAME: str = "Admin"
    DEFAULT_ADMIN_LASTNAME: str = "User"
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
print(f"Loaded PAYME_SECRET_KEY: {settings.PAYME_SECRET_KEY}")
