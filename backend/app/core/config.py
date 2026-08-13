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
        "DATABASE_URL", "postgresql://localhost/labos_db"
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

    # n8n Integration Configuration
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "")
    N8N_WEBHOOK_SECRET: str = os.getenv("N8N_WEBHOOK_SECRET", "")
    N8N_INTEGRATION_KEY: str = os.getenv("N8N_INTEGRATION_KEY", "")
    INTEGRATION_TIMEOUT_SECONDS: int = int(os.getenv("INTEGRATION_TIMEOUT_SECONDS", "15"))
    INTEGRATION_MAX_RETRIES: int = int(os.getenv("INTEGRATION_MAX_RETRIES", "3"))

    def validate_production_security(self):
        if self.ENVIRONMENT.lower() == "production":
            if not self.JWT_SECRET or "supersecret" in self.JWT_SECRET:
                raise ValueError("INSECURE CONFIGURATION: JWT_SECRET must be set to a strong secret in production!")


settings = Settings()
settings.validate_production_security()

