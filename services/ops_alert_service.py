"""
Minimal ops alerting — webhook POST when background jobs fail repeatedly.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from utils.logger import get_logger

logger = get_logger()


class OpsAlertService:
    def __init__(self) -> None:
        self.webhook_url = (os.getenv("OPS_ALERT_WEBHOOK_URL") or "").strip()

    def send_job_failure_alert(
        self,
        job_id: str,
        consecutive_failures: int,
        error: str,
    ) -> None:
        message = (
            f"[Agu AI Ops] Job `{job_id}` failed {consecutive_failures} times in a row. "
            f"Last error: {error or 'unknown'}"
        )
        logger.error(message)
        if not self.webhook_url:
            return
        payload = {
            "text": message,
            "job_id": job_id,
            "consecutive_failures": consecutive_failures,
            "error": error,
        }
        self._post_webhook(payload)

    def _post_webhook(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                if response.status >= 400:
                    logger.warning(f"[OpsAlert] Webhook returned HTTP {response.status}")
        except urllib.error.URLError as exc:
            logger.warning(f"[OpsAlert] Webhook delivery failed: {exc}")

    def send_llm_usage_alert(self, alert: dict) -> None:
        message = f"[Agu AI Ops] {alert.get('message') or 'LLM usage alert'}"
        logger.warning(message)
        if not self.webhook_url:
            return
        payload = {"text": message, "alert": alert}
        self._post_webhook(payload)


ops_alert_service = OpsAlertService()
