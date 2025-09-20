# app/config.py
import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
from dotenv import load_dotenv
load_dotenv()

class Settings(BaseSettings):
    # Application Settings
    session_ttl_hours: int = 4
    max_budget: float = 1000000
    min_budget: float = 0
    max_days: int = 30
    allowed_origins: List[str] = ["http://localhost:3000"]
    
    # Google Cloud Configuration
    project_id: str = ""
    region: str = "us-central1"
    port: int = 8080
    database: str = "(default)"
    
    # Secret Management
    google_api_key: str = ""
    service_account_key_path: str = ""
    
    # Google OAuth Configuration
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:3000/auth/callback"
    
    # Pydantic V2 configuration (Python 3.13 compatible)
    model_config = ConfigDict(
        env_file=".env",
        extra="ignore"  # Allow extra environment variables without validation errors
    )

class CloudRunConfig:
    """Configuration for Cloud Run deployment"""
    
    # Environment Detection
    IS_CLOUD_RUN: bool = os.getenv("K_SERVICE") is not None
    
    # Google Cloud Configuration
    PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    REGION: str = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    PORT: int = int(os.getenv("PORT", "8080"))
    DATABASE: str = os.getenv("DATABASE", "(default)")
    
    # Secret Manager Paths (for Cloud Run)
    @classmethod
    def get_service_account_secret_path(cls) -> str:
        return f"projects/{cls.PROJECT_ID}/secrets/service-account-key/versions/latest"
    
    @classmethod
    def get_google_api_key_secret_path(cls) -> str:
        return f"projects/{cls.PROJECT_ID}/secrets/google-api-key/versions/latest"
    
    @classmethod
    def get_secrets_config(cls) -> dict:
        """Get configuration for accessing secrets"""
        if cls.IS_CLOUD_RUN:
            return {
                "PROJECT_ID": cls.PROJECT_ID,
                "DATABASE": cls.DATABASE,
                "SERVICE_ACCOUNT_SECRET": cls.get_service_account_secret_path(),
                "GOOGLE_API_KEY_SECRET": cls.get_google_api_key_secret_path(),
            }
        else:
            # Local development fallback
            return {
                "PROJECT_ID": os.getenv("PROJECT_ID", ""),
                "DATABASE": os.getenv("DATABASE", "(default)"),
                "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
                "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
            }

settings = Settings()
cloud_config = CloudRunConfig()