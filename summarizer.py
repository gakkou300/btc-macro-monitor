import json
import re
import logging
import os
import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = (
    "あなたはビットコイン短期トレーダー向けのアナリストです。"
    "以下の経済指標・ニュースを分析し、BTCへの短期的な影響を"
    "強気・中立・弱気で判定し、根拠と合わせて日本語200字以内で要約してください。"
    "返答は必ず以下のJSON形式のみで返してください（前後の説明不要）:\n"
    '{"judgment": "強気" | "中立" | "弱気", "summary": "<200字以内の日本語>"}'
)

EMOJI_MAP = {"強気": "🟢", "中立": "🟡", "弱気": "🔴"}


def summarize(data: dict) -> dict:
    """
    Summarize indicator data using Claude.

    Handles three data shapes:
      - FOMC  : data has 'content' key
      - FRED  : data has 'date' key (no prev_value)
      - Market: data has 'prev_value' key

    Returns:
        {"judgment": str, "emoji": str, "summary": str}
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_message = _build_user_message(data)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return _parse_response(raw)
    except Exception as e:
        logger.error(f"Summarizer failed: {e}")
        return _fallback_summary(data)


def _build_user_message(data: dict) -> str:
    # SEC filing – company + form type metadata
    if data.get("key") == "sec_filing":
        return (
            f"指標: SEC新着ファイリング\n"
            f"提出者: {data['entity_name']}\n"
            f"種別: {data['form_type']}\n"
            f"日付: {data['file_date']}"
        )

    # FOMC – has document body
    if data.get("content"):
        return (
            f"指標: {data['name']}\n"
            f"日付: {data.get('date', '不明')}\n\n"
            f"本文:\n{data['content']}"
        )

    # Fear & Greed Index – zone change
    if data.get("key") == "fear_greed":
        prev_zone_label = data.get("prev_zone_label", "不明")
        return (
            f"指標: {data['name']}\n"
            f"現在値: {data['value']:.0f} ({data.get('zone_label', '不明')})\n"
            f"前回ゾーン: {prev_zone_label}\n"
            f"日付: {data.get('date', '不明')}"
        )

    # ETF Net Flows – new daily data
    if data.get("key") == "etf_flow":
        value = data["value"]
        direction = "純流入" if value >= 0 else "純流出"
        return (
            f"指標: {data['name']}\n"
            f"日次{direction}: {value:+,.0f} BTC\n"
            f"日付: {data.get('date', '不明')}"
        )

    # Funding Rate – sign flip or threshold cross
    if data.get("key") == "funding_rate":
        value = data["value"]
        prev = data.get("prev_value")
        # value is in decimal form (e.g. 0.0001 = 0.01% per 8h) → multiply by 100 for display
        prev_str = f"{prev * 100:+.4f}%" if prev is not None else "不明"
        sign_note = ""
        if data.get("sign_changed"):
            sign_note = " ⚠️ 符号反転"
        elif data.get("threshold_crossed"):
            sign_note = " ⚠️ 閾値(±0.05%)越え"
        return (
            f"指標: {data['name']}\n"
            f"現在レート: {value * 100:+.4f}%{sign_note}\n"
            f"前回レート: {prev_str}\n"
            f"取得時刻: {data.get('timestamp', '不明')}"
        )

    # Market – has prev_value for change context
    if "prev_value" in data:
        value = data["value"]
        prev = data["prev_value"]
        change_pct = data.get("change_pct", 0.0)
        change_abs = data.get("change_abs", 0.0)
        timestamp = data.get("timestamp", "不明")

        if prev is not None:
            change_str = f"{change_abs:+.4f} ({change_pct:+.2f}%)"
            prev_str = f"{prev:.4f}"
        else:
            change_str = "初回取得"
            prev_str = "不明"

        return (
            f"指標: {data['name']}\n"
            f"現在値: {value:.4f}\n"
            f"前回値: {prev_str}\n"
            f"変化: {change_str}\n"
            f"取得時刻: {timestamp}"
        )

    # FRED – latest value + release date
    return (
        f"指標: {data['name']}\n"
        f"最新値: {data.get('value', '不明')}\n"
        f"発表日: {data.get('date', '不明')}"
    )


def _parse_response(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON found in response: {raw}")
    parsed = json.loads(match.group())
    judgment = parsed.get("judgment", "中立")
    return {
        "judgment": judgment,
        "emoji": EMOJI_MAP.get(judgment, "🟡"),
        "summary": parsed.get("summary", ""),
    }


def _fallback_summary(data: dict) -> dict:
    parts = [data.get("name", "不明")]
    if data.get("date"):
        parts.append(data["date"])
    if data.get("value") is not None:
        parts.append(f"値: {data['value']}")
    if data.get("change_pct") is not None:
        parts.append(f"変化: {data['change_pct']:+.2f}%")
    return {"judgment": "中立", "emoji": "🟡", "summary": " / ".join(parts)}
