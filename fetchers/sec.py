import re
import logging
import requests
from datetime import date

logger = logging.getLogger(__name__)

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
FORMS = "8-K,S-1,19b-4"
QUERY = '"bitcoin" OR "cryptocurrency" OR "crypto" OR "stablecoin" OR "digital asset"'
PRIORITY_KEYWORDS = {"bitcoin", "crypto", "etf", "stablecoin", "enforcement"}
# SEC requires User-Agent with email address to avoid 403 blocks
# See: https://www.sec.gov/os/accessing-edgar-data
HEADERS = {"User-Agent": "BtcMacroMonitor shinonome.soccer.46@gmail.com"}


def fetch_sec_filings(start_date: str | None = None) -> list[dict]:
    """
    Fetch crypto-related SEC EDGAR filings from start_date to today.

    Args:
        start_date: ISO date string (YYYY-MM-DD). Defaults to today.

    Returns:
        List of filing dicts: {id, title, entity_name, form_type, file_date, url, priority}
    """
    today = date.today().isoformat()
    params = {
        "q": QUERY,
        "forms": FORMS,
        "dateRange": "custom",
        "startdt": start_date or today,
        "enddt": today,
    }
    resp = requests.get(EFTS_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    hits = resp.json().get("hits", {}).get("hits", [])

    results = []
    for hit in hits:
        source = hit.get("_source", {})
        filing_id = hit.get("_id", "")
        entity_name = source.get("entity_name", "不明")
        form_type = source.get("form_type", "不明")
        file_date = source.get("file_date", today)
        display_names = source.get("display_names", [])

        # Build filing index URL using CIK from display_names
        cik = _extract_cik(display_names)
        accession_no_dashes = filing_id.replace("-", "")
        if cik:
            url = (
                f"https://www.sec.gov/Archives/edgar/data"
                f"/{cik}/{accession_no_dashes}/{filing_id}-index.htm"
            )
        else:
            # Fallback: EDGAR full-text search for this accession number
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{filing_id}%22"

        # Title: company name + form type
        title = f"{entity_name} [{form_type}]"

        # Priority: any priority keyword in entity name or form type
        text = (entity_name + " " + form_type).lower()
        is_priority = any(kw in text for kw in PRIORITY_KEYWORDS)

        results.append({
            "id": filing_id,
            "title": title,
            "entity_name": entity_name,
            "form_type": form_type,
            "file_date": file_date,
            "url": url,
            "priority": is_priority,
        })

    return results


def _extract_cik(display_names: list) -> str | None:
    """Extract CIK from display_names like 'Company Name (CIK 0001234567)'."""
    for name in display_names:
        m = re.search(r"CIK[:\s]+0*(\d+)", name, re.IGNORECASE)
        if m:
            return m.group(1)
    return None
