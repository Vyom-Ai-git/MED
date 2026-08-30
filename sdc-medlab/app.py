from __future__ import annotations

import logging
import os

from flask import Flask, jsonify

from config import get_config
from routes.webhook import webhook_bp
from services.labos_client import LabOSClient
from services.labos_workflow import LabOSWorkflowService
from services.mongodb import MongoStore
from services.whatsapp import WhatsAppClient
from services.gemini import GeminiAnalyzer


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def create_app(testing: bool = False, mongo_client=None) -> Flask:
    configure_logging()
    config = get_config()

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.max_content_length
    app.config["APP_CONFIG"] = config
    app.config["SECRET_KEY"] = config.flask_secret_key or "dev-only-secret-key"

    store = MongoStore(config, client=mongo_client)
    whatsapp = WhatsAppClient(config)
    gemini = GeminiAnalyzer(config)
    labos = LabOSClient(config)
    labos_workflow = LabOSWorkflowService(store, whatsapp, gemini, labos, config)

    if testing or mongo_client is not None:
        store.ensure_indexes()

    app.config["STORE"] = store
    app.config["WHATSAPP"] = whatsapp
    app.config["GEMINI"] = gemini
    app.config["LABOS"] = labos
    app.config["LABOS_WORKFLOW"] = labos_workflow
    app.config["TESTING"] = testing

    app.register_blueprint(webhook_bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": "vyoma-automation"})

    @app.get("/health/db")
    def health_db():
        try:
            store.ping()
            return jsonify({"status": "ok", "database": config.mongodb_database})
        except Exception:
            logging.exception("DB health check failed")
            return jsonify({"status": "error"}), 503

    @app.get("/health/meta")
    def health_meta():
        return jsonify(
            {
                "status": "ok",
                "meta_configured": bool(config.meta_access_token and config.meta_phone_number_id),
                "webhook_secret_configured": bool(config.meta_verify_token),
                "gemini_configured": bool(config.gemini_api_key and config.gemini_model),
                "labos_configured": bool(
                    config.labos_base_url
                    and config.labos_integration_key
                    and config.labos_webhook_secret
                ),
                "report_ingest_configured": bool(config.report_ingest_api_key),
                "test_mode": config.test_mode,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["APP_CONFIG"].port, debug=False)
