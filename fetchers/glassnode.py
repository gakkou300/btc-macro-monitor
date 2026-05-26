import os
import logging
import requests
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"


def _get_api_key() -> str:
    key = os.environ.get("GLASSNODE_API_KEY")
    if not key:
        raise EnvironmentError("GLASSNODE_API_KEY is not set")
    return key


def _fetch(endpoint: str, params: dict) -> list:
    """Fetch a Glassnode time-series endpoint. Returns list of {t, v} dicts."""
    api_key = _get_api_key()
    params = {"a": "BTC", "api_key": api_key, **params}
    resp = requests.get(f"{GLASSNODE_BASE}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"Glassnode returned empty data for {endpoint}")
    return data


# ── Fear & Greed Index ────────────────────────────────────────────────────────

FEAR_GREED_ZONES = [
    (0,  24, "extreme_fear",  "極度の恐怖"),
    (25, 44, "fear",          "恐怖"),
    (45, 55, "neutral",       "中立"),
    (56, 75, "greed",         "強欲"),
    (76, 100, "extreme_greed", "極度の強欲"),
]


def get_fear_greed_zone(value: float) -> tuple[str, str]:
    """Return (zone_key, zone_label) for a Fear & Greed value."""
    for lo, hi, key, label in FEAR_GREED_ZONES:
        if lo <= value <= hi:
            return key, label
    return "unknown", "不明"


def fetch_fear_greed() -> dict:
    """
    Fetch the latest BTC Fear & Greed Index from Glassnode.

    Returns:
        dict with: key, name, value (int 0-100), zone, zone_label, date, url
    """
    data = _fetch("indicators/fear_greed_index", {"i": "24h"})
    latest = data[-1]
    value = float(latest["v"])
    data_date = date.fromtimestamp(latest["t"]).isoformat()
    zone, zone_label = get_fear_greed_zone(value)

    return {
        "key": "fear_greed",
        "name": "恐怖&強欲指数",
        "value": value,
        "zone": zone,
        "zone_label": zone_label,
        "date": data_date,
        "url": "https://studio.glassnode.com/metrics?a=BTC&m=indicators.FearGreed",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ── US Spot ETF Net Flows ─────────────────────────────────────────────────────

def fetch_etf_flow() -> dict:
    """
    Fetch the latest US Spot BTC ETF daily net flows from Glassnode.

    Returns:
        dict with: key, name, value (BTC float), date, url
    """
    data = _fetch("institutions/us_spot_etf_flows_net", {"i": "24h"})
    latest = data[-1]
    value = float(latest["v"])
    data_date = date.fromtimestamp(latest["t"]).isoformat()

    return {
        "key": "etf_flow",
        "name": "米国スポットBTC ETF純流入",
        "value": value,
        "date": data_date,
        "url": "https://studio.glassnode.com/metrics?a=BTC&m=institutions.UsSpotEtfFlowsNet",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ── Funding Rate (Perpetual) ──────────────────────────────────────────────────

def fetch_funding_rate() -> dict:
    """
    Fetch the latest BTC perpetual futures funding rate from Glassnode.

    Returns:
        dict with: key, name, value (float, % per 8h), date, url
    """
    data = _fetch("derivatives/futures_funding_rate_perpetual", {"i": "1h"})
    latest = data[-1]
    value = float(latest["v"])
    data_date = datetime.fromtimestamp(latest["t"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "key": "funding_rate",
        "name": "BTCパーペチュアルFunding Rate",
        "value": value,
        "date": data_date,
        "url": "https://studio.glassnode.com/metrics?a=BTC&m=derivatives.FuturesFundingRatePerpetual",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
