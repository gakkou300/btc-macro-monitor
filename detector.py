import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "state.json"

_DEFAULT_STATE: dict = {
    "cpi": {"date": None, "value": None},
    "nfp": {"date": None, "value": None},
    "fomc": {"url": None, "date": None},
}


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


def is_new_fred(key: str, current: dict) -> bool:
    """Return True if the FRED observation date is newer than the stored date."""
    state = _load_state()
    prev_date = state.get(key, {}).get("date")
    return current["date"] != prev_date


def is_new_fomc(current: dict) -> bool:
    """Return True if the FOMC document URL has changed."""
    state = _load_state()
    prev_url = state.get("fomc", {}).get("url")
    return current["url"] != prev_url


def update_fred(key: str, current: dict) -> None:
    state = _load_state()
    state[key] = {"date": current["date"], "value": current["value"]}
    _save_state(state)
    logger.info(f"[{key.upper()}] State updated: {current['date']}")


def update_fomc(current: dict) -> None:
    state = _load_state()
    state["fomc"] = {"url": current["url"], "date": current["date"]}
    _save_state(state)
    logger.info(f"[FOMC] State updated: {current['url']}")
