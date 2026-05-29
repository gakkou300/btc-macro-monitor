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


def _fetch_glassnode(endpoint: str, params: dict) -> list:
    """Fetch a Glassnode time-series endpoint. Returns list of {t, v} dicts."""
    api_key = _get_api_key()
    p = {"a": "BTC", "api_key": api_key, **params}
    resp = requests.get(f"{GLASSNODE_BASE}/{endpoint}", params=p, timeout=30)
    if not resp.ok:
        raise RuntimeError(
            f"Glassnode {endpoint} returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    data = resp.json()
    if not data:
        raise ValueError(f"Glassnode returned empty data for {endpoint}")
    return data


# ── Fear & Greed Index (Alternative.me — free, no key) ───────────────────────

_FG_ZONE_MAP = {
    "Extreme Fear":  ("extreme_fear",  "極度の恐怖"),
    "Fear":          ("fear",          "恐怖"),
    "Neutral":       ("neutral",       "中立"),
    "Greed":         ("greed",         "強欲"),
    "Extreme Greed": ("extreme_greed", "極度の強欲"),
}

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
    Fetch the latest Crypto Fear & Greed Index from Alternative.me.
    No API key required.

    Returns:
        dict with: key, name, value (0-100), zone, zone_label, date, url
    """
    resp = requests.get(
        "https://api.alternative.me/fng/",
        params={"limit": 1},
        timeout=30,
    )
    resp.raise_for_status()
    entry = resp.json()["data"][0]
    value = float(entry["value"])
    data_date = date.fromtimestamp(int(entry["timestamp"])).isoformat()
    zone, zone_label = _FG_ZONE_MAP.get(
        entry["value_classification"], ("unknown", "不明")
    )

    return {
        "key": "fear_greed",
        "name": "恐怖&強欲指数",
        "value": value,
        "zone": zone,
        "zone_label": zone_label,
        "date": data_date,
        "url": "https://alternative.me/crypto/fear-and-greed-index/",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


# ── US Spot ETF Net Flows (Glassnode) ─────────────────────────────────────────

def fetch_etf_flow() -> dict:
    """
    Fetch the latest US Spot BTC ETF daily net flows from Glassnode.

    Returns:
        dict with: key, name, value (BTC float), date, url
    """
    data = _fetch_glassnode("institutions/us_spot_etf_flows_net", {"i": "24h"})
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


# ── Funding Rate Perpetual (OKX — free, no key, globally accessible) ─────────

def fetch_funding_rate() -> dict:
    """
    Fetch the latest BTC perpetual futures funding rate from OKX.
    No API key required. Globally accessible (no geo-restriction).
    Value is in decimal form (e.g. 0.0001 = 0.01% per 8h).

    Returns:
        dict with: key, name, value (decimal float), date, url
    """
    resp = requests.get(
        "https://www.okx.com/api/v5/public/funding-rate",
        params={"instId": "BTC-USDT-SWAP"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "0":
        raise RuntimeError(f"OKX API error: {data.get('msg')}")
    entry = data["data"][0]
    value = float(entry["fundingRate"])
    data_date = datetime.fromtimestamp(
        int(entry["fundingTime"]) / 1000, tz=timezone.utc
    ).strftime("%Y-%m-%d %H:%M UTC")

    return {
        "key": "funding_rate",
        "name": "BTCパーペチュアルFunding Rate",
        "value": value,
        "date": data_date,
        "url": "https://www.okx.com/trade-swap/btc-usdt-swap",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
