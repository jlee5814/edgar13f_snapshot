from edgar13f.parse_13f import iter_info_table_rows

def test_iter_info_table_rows_parses_two():
    xml = open("tests/data/fixtures/sample_13f.xml", "r", encoding="utf-8").read()
    rows = list(iter_info_table_rows(xml))
    assert len(rows) == 2
    a, b = rows
    assert a["issuer_name"] == "Example Corp A"
    assert a["cusip"] == "123456789"
    assert a["value_usd_thousands"] == 15000
    assert a["shares"] == 1000000
    assert a["voting_sole"] == 800000
    assert b["issuer_name"] == "Example Corp B"
