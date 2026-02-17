from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from src.services.integrations.base import BaseIntegration


class SlackIntegration(BaseIntegration):
    async def send_notification(
        self,
        message: str,
        channel: Optional[str] = None,
        blocks: Optional[list] = None,
    ) -> Dict[str, Any]:
        token = self.config.get("bot_token")
        webhook_url = self.config.get("webhook_url")

        payload = {"text": message}
        if channel or self.config.get("default_channel"):
            payload["channel"] = channel or self.config.get("default_channel")
        if blocks:
            payload["blocks"] = blocks

        async with httpx.AsyncClient() as client:
            if token:
                resp = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload,
                )
                return resp.json()
            if webhook_url:
                resp = await client.post(webhook_url, json=payload)
                return {"ok": resp.status_code < 300, "status_code": resp.status_code}

        raise ValueError("Slack bot token or webhook_url not configured.")
