from __future__ import annotations

import argparse
import logging
from typing import List, Dict, Optional

from .utils import setup_logging
from .fetch import (
    resolve_cik_from_manager_name,
    load_submissions_json,
    latest_13f_accession,
    fetch_information_table_xml,
    pad_cik,
)
from .parse_13f import iter_info_table_rows
from .finance import summarize_rows
from .persist import write_csv, write_json

log = logging.getLogger(__name__)


def run(manager: Optional[str], cik: Optional[str], filing_month: Optional[str], out_csv: str, summary_json: Optional[str], user_agent: Optional[str]) -> None:
    if not (manager or cik):
        raise SystemExit("Provide either --manager or --cik")
    if manager and cik:
        raise SystemExit("Provide only one of --manager or --cik, not both")
    
    setup_logging()
    
    raw_cik: Optional[str] = cik
    if manager:
        log.info("Resolving manager name to CIK: %s", manager)
        raw_cik = resolve_cik_from_manager_name(manager, user_agent=user_agent)
        if not raw_cik:
            raise SystemExit(f"Could not resolve CIK for manager: {manager}")
        log.info("Resolved CIK: %s", raw_cik)
    
    assert raw_cik is not None
    submissions = load_submissions_json(raw_cik, user_agent=user_agent)
    latest = latest_13f_accession(submissions, filing_month=filing_month)
    if not latest:
        raise SystemExit("No 13F-HR filings found for this manager/period")
    
    accession = latest["accession"]
    manager_name = submissions.get("name", "")
    # Period-end (reportDate) may be parallel array; best-effort pick
    period_end = ""
    recent = submissions.get("filings", {}).get("recent", {})
    if "reportDate" in recent and isinstance(recent["reportDate"], list) and recent.get("accessionNumber"):
        # align accession to reportDate by index if possible
        try:
            idx = recent.get("accessionNumber", []).index(accession)
            period_end = recent.get("reportDate", [""] * (idx + 1))[idx]
        except ValueError:
            period_end = recent.get("reportDate", [""])[0] if recent.get("reportDate") else ""
    
    log.info("Latest 13F accession: %s on %s", accession, latest["filingDate"])
    xml_text = fetch_information_table_xml(raw_cik, accession, user_agent=user_agent)
    
    rows: List[Dict] = []
    for r in iter_info_table_rows(xml_text):
        r["cik"] = pad_cik(raw_cik)
        r["manager_name"] = manager_name
        r["period_end"] = period_end
        rows.append(r)
    
    log.info("Parsed %d holdings", len(rows))
    count = write_csv(out_csv, rows)
    log.info("Wrote CSV: %s (%d rows)", out_csv, count)
    
    if summary_json:
        summary = summarize_rows(rows)
        summary.update({
            "cik": pad_cik(raw_cik),
            "manager_name": manager_name,
            "period_end": period_end,
        })
        write_json(summary_json, summary)
        log.info("Wrote summary: %s", summary_json)


def main(argv: Optional[List[str]] = None) -> None:
    ap = argparse.ArgumentParser(description="EDGAR 13F Snapshot Builder (Week 1)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--manager", type=str, help="Manager name (e.g., 'Berkshire Hathaway')")
    g.add_argument("--cik", type=str, help="Manager CIK (digits only)")
    ap.add_argument("--filing-date", type=str, help="YYYY-MM (optional; default latest)")
    ap.add_argument("--out", type=str, required=True, help="Output CSV path")
    ap.add_argument("--summary", type=str, help="Optional summary JSON path")
    ap.add_argument("--user-agent", type=str, default=None, help="Custom User-Agent for SEC requests")
    args = ap.parse_args(argv)
    
    run(args.manager, args.cik, args.filing_date, args.out, args.summary, args.user_agent)


if __name__ == "__main__":
    main()
