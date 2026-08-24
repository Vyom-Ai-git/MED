from __future__ import annotations

import logging
from typing import Any

import requests


logger = logging.getLogger(__name__)


class WhatsAppError(RuntimeError):
    pass


class WhatsAppClient:
    def __init__(self, config, session: requests.Session | None = None):
        self.config = config
        self.session = session or requests.Session()
        self.timeout = 20

    def _base_url(self) -> str:
        return f"https://graph.facebook.com/{self.config.meta_api_version}/{self.config.meta_phone_number_id}/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.meta_access_token}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.config.meta_access_token or not self.config.meta_phone_number_id:
            raise WhatsAppError("Meta WhatsApp configuration is missing")

        response = self.session.post(
            self._base_url(),
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            logger.warning("WhatsApp API request failed with status %s", response.status_code)
            raise WhatsAppError(f"WhatsApp API returned HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise WhatsAppError("WhatsApp API returned non-JSON response") from exc

    def send_text(self, phone: str, text: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        return self._post(payload)

    def send_interactive_buttons(self, phone: str, body: str, buttons: list[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {
                            "type": "reply",
                            "reply": {"id": button["id"], "title": button["title"]},
                        }
                        for button in buttons
                    ]
                },
            },
        }
        return self._post(payload)

    def send_document(self, phone: str, document_url: str, filename: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename,
            },
        }
        return self._post(payload)

    def send_template(self, phone: str, template_name: str, language_code: str) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        return self._post(payload)
