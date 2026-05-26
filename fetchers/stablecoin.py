import os
import logging
import requests
from datetime import datetime, timezone, date

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
GLASSNODE_BASE = "https://api.glassnode.com/v1/metrics"

STABLECOINS: dict[str, dict] = {
    "usdt": {
        "id": "tether",
        "name": "USDT供給量",
        "symbol": "USDT",
        "url": "https://www.coingecko.com/en/coins/tether",
    },
    "usdc": {
        "id": "usd-coin",
        "name": "USDC供給量",
        "symbol": "USDC",
        "url": "https://www.coingecko.com/en/coins/usd-coin",
    },
}


def fetch_stablecoin(key: str) -> dict:
    """
    Fetch stablecoin circulating supply from CoinGecko.

    Args:
        key: 'usdt' or 'usdc'

    Returns:
        dict with: key, name, symbol, value (float), url, timestamp
    """
    info = STABLECOINS[key]
    headers = {}
    api_key = os.environ.get("COINGECKO_API_KEY")
    if api_key:
        headers["x-cg-demo-api-key"] = api_key

    resp = requests.get(
        f"{COINGECKO_BASE}/coins/{info['id']}",
        params={
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false",
        },
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    supply = float(resp.json()["market_data"]["circulating_supply"])

    return {
        "key": key,
        "name": info["name"],
        "symbol": info["symbol"],
        "value": supply,
        "url": info["url"],
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def fetch_btc_exchange_holdings() -> dict:
    """
    Fetch total BTC held across exchanges via Glassnode API.
    Uses the distribution/balance_exchanges endpoint (daily resolution).
    Requires GLASSNODE_API_KEY environment variable.

    Returns:
        dict with: key, name, symbol, value (BTC float), url, timestamp
    """
    api_key = os.environ["GLASSNODE_API_KEY"]

    resp = requests.get(
        f"{GLASSNODE_BASE}/distribution/balance_exchanges",
        params={
            "a": "BTC",
            "i": "24h",          # daily resolution
            "api_key": api_key,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if not data:
        raise ValueError("Glassnode returned empty data for balance_exchanges")

    # Response is a list of {t: timestamp, v: value}; last entry = most recent
    latest = data[-1]
    btc_total = float(latest["v"])
    data_date = date.fromtimestamp(latest["t"]).isoformat()

    return {
        "key": "btc_exchange",
        "name": "取引所BTC保有量",
        "symbol": "BTC",
        "value": btc_total,
        "data_date": data_date,
        "url": "https://studio.glassnode.com/metrics?a=BTC&m=distribution.BalanceExchanges",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }
