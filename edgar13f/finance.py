from __future__ import annotations
from typing import List, Dict

def summarize_rows(rows: List[Dict]) -> Dict:
    total = sum(r.get("value_usd_thousands", 0) for r in rows)
    rows_sorted = sorted(rows, key=lambda r: r.get("value_usd_thousands", 0), reverse=True)
    top10 = rows_sorted[:10]
    top10_sum = sum(r.get("value_usd_thousands", 0) for r in top10)
    total_b = round(total / 1_000_000.0, 3)
    top10_conc = round(top10_sum / total, 4) if total else 0.0
    top_positions = [
        {
            "issuer": r.get("issuer_name", ""),
            "value_b": round(r.get("value_usd_thousands", 0)/1_000_000.0, 3),
            "weight": round(r.get("value_usd_thousands", 0)/total, 4) if total else 0.0,
        } for r in top10
    ]
    return {
        "num_positions": len(rows),
        "sum_value_usd_b": total_b,
        "top_10_concentration": top10_conc,
        "top_positions": top_positions,
    }
