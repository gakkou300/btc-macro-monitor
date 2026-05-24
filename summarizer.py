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

    Args:
        data: dict containing 'name' and either 'content' (FOMC) or 'value'+'date' (FRED).

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
    if data.get("content"):
        return (
            f"指標: {data['name']}\n"
            f"日付: {data.get('date', '不明')}\n\n"
            f"本文:\n{data['content']}"
        )
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
    if data.get("value"):
        parts.append(f"値: {data['value']}")
    return {"judgment": "中立", "emoji": "🟡", "summary": " / ".join(parts)}
