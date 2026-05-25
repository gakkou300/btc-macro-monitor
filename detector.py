import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "state.json"

_DEFAULT_STATE: dict = {
    "cpi": {"date": None, "value": None},
    "nfp": {"date": None, "value": None},
    "fomc": {"url": None, "date": None},
    "market": {
        "dxy":    {"value": None},
        "us10y":  {"value": None},
        "nasdaq": {"value": None},
        "vix":    {"value": None},
    },
}

# Thresholds for market change detection
# type "pct" → relative change (e.g. 0.005 = 0.5%)
# type "abs" → absolute change (e.g. 0.03 = 3bp for us10y which is in % points)
_MARKET_THRESHOLDS: dict[str, dict] = {
    "dxy":    {"type": "pct", "value": 0.005},
    "us10y":  {"type": "abs", "value": 0.03},
    "nasdaq": {"type": "pct", "value": 0.010},
    "vix":    {"type": "pct", "value": 0.10},
}

_VIX_PRIORITY_LEVEL = 20.0  # VIX > 20 and rapid change → priority alert


# ── internal helpers ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("state.json is corrupt; resetting to defaults")
    return {k: dict(v) for k, v in _DEFAULT_STATE.items()}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── FRED ──────────────────────────────────────────────────────────────────────

def is_new_fred(key: str, current: dict) -> bool:
    """Return True if the FRED observation date is newer than the stored date."""
    state = _load_state()
    prev_date = state.get(key, {}).get("date")
    return current["date"] != prev_date


def update_fred(key: str, current: dict) -> None:
    state = _load_state()
    state[key] = {"date": current["date"], "value": current["value"]}
    _save_state(state)
    logger.info(f"[{key.upper()}] State updated: {current['date']}")


# ── FOMC ──────────────────────────────────────────────────────────────────────

def is_new_fomc(current: dict) -> bool:
    """Return True if the FOMC document URL has changed."""
    state = _load_state()
    prev_url = state.get("fomc", {}).get("url")
    return current["url"] != prev_url


def update_fomc(current: dict) -> None:
    state = _load_state()
    state["fomc"] = {"url": current["url"], "date": current["date"]}
    _save_state(state)
    logger.info(f"[FOMC] State updated: {current['url']}")


# ── Market ────────────────────────────────────────────────────────────────────

def check_market_change(key: str, current_value: float) -> dict:
    """
    Check whether a market indicator has moved beyond its threshold.

    Returns:
        changed   (bool)  – True if threshold exceeded
        priority  (bool)  – True for VIX > 20 + large move
        prev_value (float | None)
        change_pct (float) – percentage change (e.g. 0.52 means +0.52%)
        change_abs (float) – absolute change
    """
    state = _load_state()
    raw_prev = state.get("market", {}).get(key, {}).get("value")

    if raw_prev is None:
        # First observation — always store, always notify
        return {
            "changed": True,
            "priority": key == "vix" and current_value > _VIX_PRIORITY_LEVEL,
            "prev_value": None,
            "change_pct": 0.0,
            "change_abs": 0.0,
        }

    prev_value = float(raw_prev)
    change_abs = current_value - prev_value
    change_pct = (change_abs / prev_value * 100) if prev_value != 0 else 0.0

    cfg = _MARKET_THRESHOLDS[key]
    if cfg["type"] == "pct":
        changed = abs(change_pct / 100) >= cfg["value"]
    else:
        changed = abs(change_abs) >= cfg["value"]

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
