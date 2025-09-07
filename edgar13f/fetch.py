from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

import requests
from .utils import sec_headers, polite_sleep

log = logging.getLogger(__name__)


class HTTPError(Exception):
    pass


def http_get(
    url: str,
    *,
    timeout: float = 15.0,
    retries: int = 3,
    sleep_s: float = 0.5,
    user_agent: str | None = None,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=sec_headers(user_agent), timeout=timeout)
            if resp.status_code in (429, 503):
                wait = min(10.0, attempt * 1.5)
                log.warning(
                    "Rate-limited or unavailable (%s). Sleeping %.1fs",
                    resp.status_code,
                    wait,
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            polite_sleep(sleep_s)
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt == retries:
                break
            wait = 1.0 * attempt
            log.warning(
                "GET failed (attempt %d/%d): %s; retrying in %.1fs",
                attempt,
                retries,
                e,
                wait,
            )
            time.sleep(wait)
    raise HTTPError(f"GET {url} failed after {retries} attempts: {last_exc}")


def pad_cik(cik: str) -> str:
    return cik.zfill(10)


def resolve_cik_from_manager_name(name: str, *, user_agent: str | None = None) -> Optional[str]:
    """
    Resolve a manager name to CIK using SEC company browse (Atom feed).
    Returns a raw CIK string (no padding) or None if not found.
    """
    import urllib.parse

    q = urllib.parse.quote(name)
    url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={q}&owner=exclude&action=getcompany&output=atom"
    resp = http_get(url, user_agent=user_agent)
    text = resp.text
    m = re.search(r"CIK=(\d{1,10})", text)
    if m:
        return m.group(1)
    return None


def load_submissions_json(cik: str, *, user_agent: str | None = None) -> Dict[str, Any]:
    url = f"https://data.sec.gov/submissions/CIK{pad_cik(cik)}.json"
    return http_get(url, user_agent=user_agent).json()


def latest_13f_accession(
    submissions: Dict[str, Any], *, filing_month: str | None = None
) -> Optional[Dict[str, str]]:
    """
    Return dict with {accession, filingDate} for latest 13F-HR, optionally filtered by 'YYYY-MM'.
    """
    recent = submissions.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accs = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    for form, acc, dt in zip(forms, accs, dates):
        if form != "13F-HR":
            continue
        if filing_month and not dt.startswith(filing_month):
            continue
        return {"accession": acc, "filingDate": dt}
    return None


# ---- Directory listing helpers (JSON first, then HTML fallback) ----

def index_listing_for_accession(
    cik_dir: str, accession_nodash: str, *, user_agent: str | None = None
) -> dict:
    """
    Return a normalized listing dict: {"files": [{"name": "..."} ...]}
    Tries JSON first; if missing, parses the HTML index page or directory listing.
    """
    # Try JSON sidecar
    json_url = f"https://sec.gov/Archives/edgar/data/{cik_dir}/{accession_nodash}/index.json"
    try:
        j = http_get(json_url, user_agent=user_agent).json()
        items = j.get("directory", {}).get("item", [])
        return {"files": [{"name": it.get("name", "")} for it in items]}
    except Exception:
        pass  # fall through to HTML

    # HTML fallback
    from bs4 import BeautifulSoup

    candidates = [
        # canonical index html (many filings expose this)
        f"https://sec.gov/Archives/edgar/data/{cik_dir}/{accession_nodash}/{accession_nodash[:10]}-{accession_nodash[10:12]}-{accession_nodash[12:]}-index.html",
        # plain directory listing (what you screenshotted)
        f"https://sec.gov/Archives/edgar/data/{cik_dir}/{accession_nodash}/",
    ]
    for url in candidates:
        try:
            html = http_get(url, user_agent=user_agent).text
            soup = BeautifulSoup(html, "lxml")
            files = []
            for a in soup.find_all("a", href=True):
                name = a["href"].split("/")[-1].split("?")[0]
                if not name or name in (".", ".."):
                    continue
                files.append({"name": name})
            if files:
                seen, uniq = set(), []
                for f in files:
                    n = f["name"]
                    if n not in seen:
                        seen.add(n)
                        uniq.append(f)
                return {"files": uniq}
        except Exception:
            continue
    raise HTTPError(f"Could not list files for {cik_dir}/{accession_nodash} via JSON or HTML")


def find_information_table_filename(listing: dict) -> str | None:
    files = [f.get("name", "").lower() for f in listing.get("files", [])]

    # Prefer canonical names
    for n in files:
        if n.endswith(".xml") and (
            "informationtable" in n or "infotable" in n or "form13finfo" in n
        ):
            return n

    # Fallback: any non-primary_doc XML (the info table is usually not primary_doc.xml)
    for n in files:
        if n.endswith(".xml") and n != "primary_doc.xml":
            return n

    # Last-ditch: if only primary_doc.xml exists, use it (some filers embed the table there)
    for n in files:
        if n == "primary_doc.xml":
            return n

    return None


# ---- Fetch information table (try manager CIK, then accession-prefix CIK) ----

def fetch_information_table_xml(
    cik: str, accession: str, *, user_agent: str | None = None
) -> str:
    """
    Fetch the 13F information-table XML by trying both possible archive owners:
    1) reporting manager CIK, then
    2) accession prefix CIK (first 10 digits of accession).
    """
    nodash = accession.replace("-", "")
    candidates: list[tuple[str, str]] = [(str(int(cik)), nodash)]
    # accession prefix CIK sometimes owns the folder
    try:
        prefix_cik = str(int(accession.split("-")[0]))
        if prefix_cik not in (c[0] for c in candidates):
            candidates.append((prefix_cik, nodash))
    except Exception:
        pass

    last_err: Optional[Exception] = None
    for cik_dir, nd in candidates:
        try:
            listing = index_listing_for_accession(cik_dir, nd, user_agent=user_agent)
            fname = find_information_table_filename(listing)
            if not fname:
                continue
            url = f"https://sec.gov/Archives/edgar/data/{cik_dir}/{nd}/{fname}"
            return http_get(url, user_agent=user_agent).text
        except Exception as e:
            last_err = e
            continue

    raise HTTPError(
        f"Could not fetch information table for accession {accession}: {last_err}"
    )