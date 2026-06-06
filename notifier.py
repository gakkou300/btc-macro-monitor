import os
import logging
import requests

logger = logging.getLogger(__name__)


# ── Phase 1 & 2: Claude-summarized notifications ──────────────────────────────

def notify(
    indicator_name: str,
    summary_result: dict,
    source_url: str,
    published_date: str,
) -> None:
    """Send an analysis result notification (Claude summary) via Discord Webhook."""
    message = (
        f"**【BTC Monitor】{indicator_name}**\n"
        f"{summary_result['emoji']} {summary_result['judgment']}\n\n"
        f"{summary_result['summary']}\n\n"
        f"🔗 {source_url}\n"
        f"📅 {published_date}"
    )
    _send(message)


# ── Phase 3: SEC filing notification ──────────────────────────────────────────

def notify_sec(filing: dict, summary_result: dict | None = None) -> None:
    """Send a SEC EDGAR filing notification with optional Claude summary."""
    priority_flag = "🚨 優先" if filing["priority"] else "📄 通常"
    summary_block = ""
    if summary_result:
        summary_block = (
            f"{summary_result['emoji']} {summary_result['judgment']}\n"
            f"{summary_result['summary']}\n\n"
        )
    message = (
        f"**【BTC Monitor】📋 SEC新着ファイリング**\n"
        f"{priority_flag}\n\n"
        f"タイトル: {filing['title']}\n"
        f"提出者: {filing['entity_name']}\n"
        f"種別: {filing['form_type']}\n\n"
        f"{summary_block}"
        f"🔗 {filing['url']}\n"
        f"📅 {filing['file_date']}"
    )
    _send(message)


# ── Phase 3: Stablecoin / Liquidity change notification ───────────────────────

def notify_change(
    indicator_name: str,
    value: float,
    prev_value: float | None,
    change_pct: float,
    timestamp: str,
    unit: str = "",
) -> None:
    """Send a quantitative change notification (no Claude summary)."""
    direction_emoji = "📈" if change_pct >= 0 else "📉"
    direction_text = "増加" if change_pct >= 0 else "減少"

    # Format value with unit-appropriate scale
    if value >= 1_000_000_000:
        value_str = f"{value / 1_000_000_000:.3f}B"
    elif value >= 1_000_000:
        value_str = f"{value / 1_000_000:.3f}M"
    else:
        value_str = f"{value:,.4f}"
    if unit:
        value_str += f" {unit}"

    change_str = f"{change_pct:+.2f}%" if prev_value is not None else "初回取得"

    message = (
        f"**【BTC Monitor】{indicator_name}**\n"
        f"{direction_emoji} {direction_text}\n\n"
        f"現在値: {value_str}\n"
        f"前回比: {change_str}\n"
        f"📅 {timestamp}"
    )
    _send(message)


# ── Error notification ─────────────────────────────────────────────────────────

def notify_error(indicator_name: str) -> None:
    """Send an error notification via Discord Webhook."""
    _send(f"**【BTC Monitor】** ⚠️ {indicator_name}の取得に失敗しました")


# ── Internal ───────────────────────────────────────────────────────────────────

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
