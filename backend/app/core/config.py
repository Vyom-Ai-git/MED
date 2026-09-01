import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the workspace
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

class Settings:
    PROJECT_NAME: str = "Vyoma LabOS"
    API_V1_STR: str = "/api/v1"
    
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./labos.db"
    )
    
    # Security
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET", "supersecretchangeinproduction1234567890abc"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    
    # CORS
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS_ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            f"{os.getenv('FRONTEND_URL', 'http://localhost:3000')},http://localhost:3000,http://127.0.0.1:3000",
        ).split(",")
        if origin.strip()
    ]

    # Native Flask workflow configuration
    FLASK_WORKFLOW_URL: str = os.getenv("FLASK_WORKFLOW_URL", "")
    FLASK_WORKFLOW_SECRET: str = os.getenv(
        "FLASK_WORKFLOW_SECRET", os.getenv("LABOS_WEBHOOK_SECRET", "")
    )
    LABOS_API_KEY: str = os.getenv("LABOS_API_KEY", os.getenv("LABOS_INTEGRATION_KEY", ""))
    INTEGRATION_TIMEOUT_SECONDS: int = int(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "15"))
    INTEGRATION_MAX_RETRIES: int = int(os.getenv("INTEGRATION_MAX_RETRIES", "3"))

    # AI Report Assistant (Gemini) — read from environment only, never hardcoded.
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", os.getenv("AI_API_KEY", ""))
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", os.getenv("AI_MODEL", "gemini-2.0-flash"))

    # Public verification links (QR codes on reports point here)
    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", FRONTEND_URL)
    REPORT_VERIFY_TOKEN_DAYS: int = int(os.getenv("REPORT_VERIFY_TOKEN_DAYS", "365"))

    def validate_production_security(self):
        if self.ENVIRONMENT.lower() == "production":
            if not self.JWT_SECRET or "supersecret" in self.JWT_SECRET:
                raise ValueError("INSECURE CONFIGURATION: JWT_SECRET must be set to a strong secret in production!")


settings = Settings()
settings.validate_production_security()

