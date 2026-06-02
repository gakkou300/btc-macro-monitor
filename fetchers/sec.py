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
        # _id format is "{accession_number}:{filename}", e.g. "0001477932-26-003478:class_ex991.htm"
        accession = filing_id.split(":")[0]  # "0001477932-26-003478"

        display_names = source.get("display_names", [])

        # entity_name may be empty in EFTS response — fall back to display_names
        entity_name = source.get("entity_name", "") or ""
        if not entity_name and display_names:
            # display_names entries look like "Company Name (CIK 0001234567)"
            entity_name = display_names[0].split(" (CIK")[0].strip()
        entity_name = entity_name or "不明"

        # form_type may be absent for exhibit documents — fall back to submissions API
        form_type = source.get("form_type") or ""

        # Build filing index URL using CIK from display_names
        cik = _extract_cik(display_names)

        if not form_type and cik:
            form_type = _fetch_form_type_by_cik(cik, accession)
        form_type = form_type or "不明"

        file_date = source.get("file_date", today)
        accession_no_dashes = accession.replace("-", "")
        if cik:
            url = (
                f"https://www.sec.gov/Archives/edgar/data"
                f"/{cik}/{accession_no_dashes}/{accession}-index.htm"
            )
        else:
            # Fallback: EDGAR full-text search for this accession number
            url = f"https://efts.sec.gov/LATEST/search-index?q=%22{accession}%22"

        # Title: company name + form type
        title = f"{entity_name} [{form_type}]"

        # Priority: any priority keyword in entity name or form type
        text = (entity_name + " " + form_type).lower()
        is_priority = any(kw in text for kw in PRIORITY_KEYWORDS)

        results.append({
            "key": "sec_filing",
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


def _fetch_form_type_by_cik(cik: str, accession: str) -> str:
    """
    Look up form type from EDGAR company submissions API.
    Used as fallback when EFTS _source.form_type is absent (e.g. exhibit documents).

    Args:
        cik: Company CIK as string (without leading zeros)
        accession: Accession number with dashes, e.g. "0001477932-26-003478"

    Returns:
        Form type string (e.g. "8-K") or empty string if not found.
    """
    try:
        padded = f"CIK{cik.zfill(10)}"
        resp = requests.get(
            f"https://data.sec.gov/submissions/{padded}.json",
            headers=HEADERS,
            timeout=10,
        )
        if not resp.ok:
            logger.warning(f"[SEC] submissions API returned {resp.status_code} for CIK {cik}")
            return ""
        recent = resp.json().get("filings", {}).get("recent", {})
        accession_numbers = recent.get("accessionNumber", [])
        forms = recent.get("form", [])
        for i, acc in enumerate(accession_numbers):
            if acc == accession:
                return forms[i]
        logger.debug(f"[SEC] Accession {accession} not found in recent filings for CIK {cik}")
        return ""
    except Exception as e:
        logger.warning(f"[SEC] Failed to fetch form type for CIK {cik}: {e}")
        return ""
