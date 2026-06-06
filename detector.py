import copy
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "state.json"

_DEFAULT_STATE: dict = {
    # Phase 1
    "cpi":    {"date": None, "value": None},
    "nfp":    {"date": None, "value": None},
    "unrate": {"date": None, "value": None},
    "icsa":   {"date": None, "value": None},
    "fomc":   {"url": None, "date": None},
    # Phase 2
    "market": {
        "dxy":    {"value": None},
        "us10y":  {"value": None},
        "nasdaq": {"value": None},
        "vix":    {"value": None},
    },
    # Phase 3
    "sec": {"date": None, "seen_ids": []},
    "stablecoin": {
        "usdt":         {"value": None},
        "usdc":         {"value": None},
        "btc_exchange": {"value": None},
    },
    "liquidity": {
        "m2sl":  {"date": None, "value": None},
        "walcl": {"date": None, "value": None},
    },
    # Phase 4: Glassnode on-chain
    "glassnode": {
        "fear_greed":   {"value": None, "zone": None, "date": None},
        "etf_flow":     {"date": None, "value": None},
        "funding_rate": {"value": None},
    },
}

# Phase 2: market thresholds
# type "pct" → relative change; type "abs" → absolute change
_MARKET_THRESHOLDS: dict[str, dict] = {
    "dxy":    {"type": "pct", "value": 0.005},   # 0.5%
    "us10y":  {"type": "abs", "value": 0.03},    # 3bp (TNX is in % points)
    "nasdaq": {"type": "pct", "value": 0.010},   # 1.0%
    "vix":    {"type": "pct", "value": 0.10},    # 10%
}
_VIX_PRIORITY_LEVEL = 20.0


# ── internal helpers ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("state.json is corrupt; resetting to defaults")
    return copy.deepcopy(_DEFAULT_STATE)


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _check_pct_change(
    prev_value: float | None, current_value: float, threshold_pct: float
) -> dict:
    """Generic percentage-change threshold check. Returns change info dict."""
    if prev_value is None:
        return {"changed": True, "prev_value": None, "change_pct": 0.0, "change_abs": 0.0}
    change_abs = current_value - prev_value
    change_pct = (change_abs / prev_value * 100) if prev_value != 0 else 0.0
    return {
        "changed": abs(change_pct) >= threshold_pct,
        "prev_value": prev_value,
        "change_pct": change_pct,
        "change_abs": change_abs,
    }


# ── Phase 1: FRED ─────────────────────────────────────────────────────────────

def is_new_fred(key: str, current: dict) -> bool:
    """Return True if the FRED observation date is newer than stored."""
    state = _load_state()
    return current["date"] != state.get(key, {}).get("date")


def update_fred(key: str, current: dict) -> None:
    state = _load_state()
    state[key] = {"date": current["date"], "value": current["value"]}
    _save_state(state)
    logger.info(f"[{key.upper()}] State updated: {current['date']}")


# ── Phase 1: FOMC ─────────────────────────────────────────────────────────────

def is_new_fomc(current: dict) -> bool:
    """Return True if the FOMC document URL has changed."""
    state = _load_state()
    return current["url"] != state.get("fomc", {}).get("url")


def update_fomc(current: dict) -> None:
    state = _load_state()
    state["fomc"] = {"url": current["url"], "date": current["date"]}
    _save_state(state)
    logger.info(f"[FOMC] State updated: {current['url']}")


# ── Phase 2: Market ───────────────────────────────────────────────────────────

def check_market_change(key: str, current_value: float) -> dict:
    """Check whether a market indicator has moved beyond its threshold."""
    state = _load_state()
    raw_prev = state.get("market", {}).get(key, {}).get("value")
    prev_value = float(raw_prev) if raw_prev is not None else None

    if prev_value is None:
        return {
            "changed": True,
            "priority": key == "vix" and current_value > _VIX_PRIORITY_LEVEL,
            "prev_value": None,
            "change_pct": 0.0,
            "change_abs": 0.0,
        }

    change_abs = current_value - prev_value
    change_pct = (change_abs / prev_value * 100) if prev_value != 0 else 0.0
    cfg = _MARKET_THRESHOLDS[key]
    changed = (
        abs(change_pct / 100) >= cfg["value"]
        if cfg["type"] == "pct"
        else abs(change_abs) >= cfg["value"]
    )
    priority = key == "vix" and changed and current_value > _VIX_PRIORITY_LEVEL

    return {
        "changed": changed,
        "priority": priority,
        "prev_value": prev_value,
        "change_pct": change_pct,
        "change_abs": change_abs,
    }


def update_market(key: str, value: float) -> None:
    state = _load_state()
    state.setdefault("market", {})[key] = {"value": value}
    _save_state(state)
    logger.info(f"[{key.upper()}] Market state updated: {value}")


# ── Phase 3: SEC ──────────────────────────────────────────────────────────────

def get_unseen_sec_filings(filings: list[dict]) -> list[dict]:
    """Return filings whose IDs have not been notified today."""
    state = _load_state()
    sec_state = state.get("sec", {})
    today = date.today().isoformat()
    # Reset seen_ids each new calendar day
    seen_ids = (
        set(sec_state.get("seen_ids", []))
        if sec_state.get("date") == today
        else set()
    )
    return [f for f in filings if f["id"] not in seen_ids]


def update_sec(new_filings: list[dict]) -> None:
    state = _load_state()
    today = date.today().isoformat()
    sec_state = state.get("sec", {})
    seen_ids = (
        set(sec_state.get("seen_ids", []))
        if sec_state.get("date") == today
        else set()
    )
    for f in new_filings:
        seen_ids.add(f["id"])
    # Cap at 200 to prevent state.json from growing unbounded
    state["sec"] = {"date": today, "seen_ids": list(seen_ids)[-200:]}
    _save_state(state)
    logger.info(f"[SEC] State updated: {len(new_filings)} new filing(s) recorded")


# ── Phase 3: Stablecoin & BTC exchange holdings ───────────────────────────────

def check_stablecoin_change(key: str, current_value: float) -> dict:
    """Check USDT/USDC supply change (threshold: ±2%)."""
    state = _load_state()
    raw = state.get("stablecoin", {}).get(key, {}).get("value")
    prev = float(raw) if raw is not None else None
    return _check_pct_change(prev, current_value, threshold_pct=2.0)


def check_btc_exchange_change(current_value: float) -> dict:
    """Check total exchange BTC holdings change (threshold: ±1%)."""
    state = _load_state()
    raw = state.get("stablecoin", {}).get("btc_exchange", {}).get("value")
    prev = float(raw) if raw is not None else None
    return _check_pct_change(prev, current_value, threshold_pct=1.0)


def update_stablecoin(key: str, value: float) -> None:
    state = _load_state()
    state.setdefault("stablecoin", {})[key] = {"value": value}
    _save_state(state)
    logger.info(f"[{key.upper()}] Stablecoin state updated: {value:,.0f}")


# ── Phase 3: Liquidity (FRED M2/WALCL) ───────────────────────────────────────

def check_liquidity_change(key: str, current_date: str, current_value: float) -> dict:
    """Check FRED liquidity change (threshold: ±0.5%, new date only)."""
    state = _load_state()
    liq = state.get("liquidity", {}).get(key, {})
    prev_date = liq.get("date")
    raw = liq.get("value")
    prev_value = float(raw) if raw is not None else None

    if current_date == prev_date:
        return {"changed": False, "prev_value": prev_value, "change_pct": 0.0, "change_abs": 0.0}

    return _check_pct_change(prev_value, current_value, threshold_pct=0.5)


def update_liquidity(key: str, date_str: str, value: float) -> None:
    state = _load_state()
    state.setdefault("liquidity", {})[key] = {"date": date_str, "value": value}
    _save_state(state)
    logger.info(f"[{key.upper()}] Liquidity state updated: {date_str} / {value}")


# ── Phase 4: Glassnode on-chain ───────────────────────────────────────────────

def check_fear_greed_change(current_value: float, current_zone: str) -> dict:
    """Notify when the Fear & Greed zone changes (e.g. fear → greed)."""
    state = _load_state()
    fg = state.get("glassnode", {}).get("fear_greed", {})
    prev_zone = fg.get("zone")
    prev_value = fg.get("value")

    if prev_zone is None:
        # First run — store but don't alert
        return {
            "changed": False,
            "prev_zone": None,
            "prev_value": None,
        }

    return {
        "changed": current_zone != prev_zone,
        "prev_zone": prev_zone,
        "prev_value": float(prev_value) if prev_value is not None else None,
    }


def update_fear_greed(value: float, zone: str, date_str: str) -> None:
    state = _load_state()
    state.setdefault("glassnode", {})["fear_greed"] = {
        "value": value,
        "zone": zone,
        "date": date_str,
    }
    _save_state(state)
    logger.info(f"[FEAR_GREED] State updated: {value:.1f} / {zone} / {date_str}")


def check_etf_flow_change(current_date: str) -> dict:
    """Notify whenever a new daily ETF flow data point appears."""
    state = _load_state()
    prev_date = state.get("glassnode", {}).get("etf_flow", {}).get("date")
    return {
        "changed": current_date != prev_date,
        "prev_date": prev_date,
    }


def update_etf_flow(date_str: str, value: float) -> None:
    state = _load_state()
    state.setdefault("glassnode", {})["etf_flow"] = {
        "date": date_str,
        "value": value,
    }
    _save_state(state)
    logger.info(f"[ETF_FLOW] State updated: {date_str} / {value:+,.2f} BTC")


_FUNDING_RATE_THRESHOLD = 0.0005  # 0.05% per 8h


def check_funding_rate_change(current_value: float) -> dict:
    """
    Notify on sign flip (positive ↔ negative) or when |rate| crosses the
    0.05% threshold going from below to above (or above to below).
    """
    state = _load_state()
    raw = state.get("glassnode", {}).get("funding_rate", {}).get("value")
    prev_value = float(raw) if raw is not None else None

    if prev_value is None:
        return {"changed": False, "prev_value": None}

    sign_changed = (current_value >= 0) != (prev_value >= 0)
    prev_extreme = abs(prev_value) >= _FUNDING_RATE_THRESHOLD
    curr_extreme = abs(current_value) >= _FUNDING_RATE_THRESHOLD
    threshold_crossed = prev_extreme != curr_extreme

    return {
        "changed": sign_changed or threshold_crossed,
        "prev_value": prev_value,
        "sign_changed": sign_changed,
        "threshold_crossed": threshold_crossed,
    }


def update_funding_rate(value: float) -> None:
    state = _load_state()
    state.setdefault("glassnode", {})["funding_rate"] = {"value": value}
    _save_state(state)
    logger.info(f"[FUNDING_RATE] State updated: {value:+.6f}")
