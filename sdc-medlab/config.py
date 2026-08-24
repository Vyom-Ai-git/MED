from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Config:
    mongodb_uri: str
    mongodb_database: str
    flask_env: str
    flask_secret_key: str
    meta_verify_token: str
    meta_access_token: str
    meta_phone_number_id: str
    meta_api_version: str
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_verify_token: str
    labos_access_token: str
    gemini_api_key: str
    gemini_model: str
    ai_api_key: str
    ai_model: str
    app_env: str
    port: int
    test_mode: bool
    test_phone_number: str
    report_ingest_api_key: str
    report_max_file_mb: int
    report_storage_dir: str
    labos_base_url: str
    labos_integration_key: str
    labos_webhook_secret: str
    labos_timeout_seconds: int
    labos_max_retries: int
    session_timeout_minutes: int
    public_base_url: str
    max_content_length: int

    @classmethod
    def from_env(cls) -> "Config":
        report_max_file_mb = int(os.getenv("REPORT_MAX_FILE_MB", "25"))
        flask_env = os.getenv("FLASK_ENV", os.getenv("APP_ENV", "development"))
        flask_secret_key = os.getenv("FLASK_SECRET_KEY", "")
        meta_verify_token = os.getenv("META_VERIFY_TOKEN", os.getenv("WHATSAPP_VERIFY_TOKEN", ""))
        meta_access_token = os.getenv("META_ACCESS_TOKEN", os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
        meta_phone_number_id = os.getenv("META_PHONE_NUMBER_ID", os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
        gemini_api_key = os.getenv("GEMINI_API_KEY", os.getenv("AI_API_KEY", ""))
        gemini_model = os.getenv("GEMINI_MODEL", os.getenv("AI_MODEL", ""))
        labos_access_token = os.getenv("LABOS_ACCESS_TOKEN", os.getenv("LABOS_BEARER_TOKEN", ""))
        return cls(
            mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017/"),
            mongodb_database=os.getenv("MONGODB_DATABASE", "medlab"),
            flask_env=flask_env,
            flask_secret_key=flask_secret_key,
            meta_verify_token=meta_verify_token,
            meta_access_token=meta_access_token,
            meta_phone_number_id=meta_phone_number_id,
            meta_api_version=os.getenv("META_API_VERSION", "v22.0"),
            whatsapp_access_token=meta_access_token,
            whatsapp_phone_number_id=meta_phone_number_id,
            whatsapp_verify_token=meta_verify_token,
            gemini_api_key=gemini_api_key,
            gemini_model=gemini_model,
            ai_api_key=gemini_api_key,
            ai_model=gemini_model,
            app_env=flask_env,
            port=int(os.getenv("PORT", "5000")),
            test_mode=os.getenv("TEST_MODE", "false").lower() == "true",
            test_phone_number=os.getenv("TEST_PHONE_NUMBER", ""),
            report_ingest_api_key=os.getenv("REPORT_INGEST_API_KEY", ""),
            report_max_file_mb=report_max_file_mb,
            report_storage_dir=os.getenv("REPORT_STORAGE_DIR", "storage/reports"),
            labos_base_url=os.getenv("LABOS_BASE_URL", ""),
            labos_integration_key=os.getenv("LABOS_INTEGRATION_KEY", ""),
            labos_webhook_secret=os.getenv("LABOS_WEBHOOK_SECRET", ""),
            labos_access_token=labos_access_token,
            labos_timeout_seconds=int(os.getenv("LABOS_TIMEOUT_SECONDS", "15")),
            labos_max_retries=int(os.getenv("LABOS_MAX_RETRIES", "3")),
            session_timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "1440")),
            public_base_url=os.getenv("PUBLIC_BASE_URL", ""),
            max_content_length=report_max_file_mb * 1024 * 1024,
        )


def get_config() -> Config:
    return Config.from_env()
