# EDGAR 13F Snapshot Builder (Week 1)

Single-threaded CLI that fetches a manager's latest 13F-HR, parses the information table, and writes a CSV + optional JSON summary.

## Usage

```bash
# Python module invocation
python -m edgar13f.main --manager "Berkshire Hathaway" --out data/berkshire.csv --summary data/summary.json

# Or with a known CIK
python -m edgar13f.main --cik 0001067983 --out data/berkshire.csv --summary data/summary.json
```

python -m edgar13f.main --cik 0001649339 --out data/scion.csv --summary data/summary.json


**Flags**
- `--manager` OR `--cik` (one required)
- `--filing-date YYYY-MM` (optional; defaults to latest)
- `--out` CSV path (required)
- `--summary` JSON summary path (optional)
- `--user-agent` (optional; SEC-friendly UA recommended)

## Dev

- Python 3.10+ recommended.
- Install: `pip install requests beautifulsoup4 lxml pytest` (tests run offline via fixtures).

## Notes

- Respect SEC rate limits and robots.txt.
- Week 1 build is single-threaded; concurrency and more features come later.
- The summary interprets `value` fields as **thousands of USD**.
