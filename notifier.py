import os
import logging
import requests

logger = logging.getLogger(__name__)


def notify(
    indicator_name: str,
    summary_result: dict,
    source_url: str,
    published_date: str,
) -> None:
    """Send an analysis result notification via Discord Webhook."""
    message = (
        f"**【BTC Monitor】{indicator_name}**\n"
        f"{summary_result['emoji']} {summary_result['judgment']}\n\n"
        f"{summary_result['summary']}\n\n"
        f"🔗 {source_url}\n"
        f"📅 {published_date}"
    )
    _send(message)


def notify_error(indicator_name: str) -> None:
    """Send an error notification via Discord Webhook."""
    _send(f"**【BTC Monitor】** ⚠️ {indicator_name}の取得に失敗しました")


def _send(message: str) -> None:
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    resp = requests.post(
        webhook_url,
        json={"content": message},
        timeout=10,
    )
    if resp.status_code not in (200, 204):
        logger.error(f"Discord Webhook failed: {resp.status_code} {resp.text}")
    else:
        logger.info("Discord Webhook sent successfully")
