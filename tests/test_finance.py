from edgar13f.finance import summarize_rows

def test_summarize_rows_top10():
    rows = [
        {"issuer_name": "A", "value_usd_thousands": 9000},
        {"issuer_name": "B", "value_usd_thousands": 1000},
    ]
    s = summarize_rows(rows)
    assert s["num_positions"] == 2
    assert s["sum_value_usd_b"] == 0.01  # 10,000k = $10,000,000 -> 0.01B
    assert round(s["top_10_concentration"], 2) == 0.9
    assert s["top_positions"][0]["issuer"] == "A"
