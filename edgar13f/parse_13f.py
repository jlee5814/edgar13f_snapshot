from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, Iterator

NS = {"n": "http://www.sec.gov/edgar/document/thirteenf/informationtable"}

def _get_text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def iter_info_table_rows(xml_text: str) -> Iterator[Dict]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}")
    
    nodes = root.findall(".//n:infoTable", NS)
    if not nodes:
        nodes = root.findall(".//infoTable")
    
    for info in nodes:
        def f(path: str) -> str:
            if path.startswith("n:"):
                return _get_text(info.find(path, NS))
            return _get_text(info.find(path))
        
        issuer = f("n:nameOfIssuer") or f("nameOfIssuer")
        cusip = f("n:cusip") or f("cusip")
        value = f("n:value") or f("value")
        ssh_amt = f("n:shrsOrPrnAmt/n:sshPrnamt") or f("shrsOrPrnAmt/sshPrnamt")
        ssh_type = f("n:shrsOrPrnAmt/n:sshPrnamtType") or f("shrsOrPrnAmt/sshPrnamtType")
        put_call = f("n:putCall") or f("putCall")
        discretion = f("n:investmentDiscretion") or f("investmentDiscretion")
        v_sole = f("n:votingAuthority/n:Sole") or f("votingAuthority/Sole")
        v_shared = f("n:votingAuthority/n:Shared") or f("votingAuthority/Shared")
        v_none = f("n:votingAuthority/n:None") or f("votingAuthority/None")
        
        def as_int(s: str) -> int:
            try:
                return int(s.replace(",", "").strip())
            except Exception:
                return 0
        
        yield {
            "issuer_name": issuer,
            "cusip": cusip,
            "value_usd_thousands": as_int(value),
            "shares": as_int(ssh_amt),
            "share_type": ssh_type,
            "put_call": put_call,
            "discretion": discretion,
            "voting_sole": as_int(v_sole),
            "voting_shared": as_int(v_shared),
            "voting_none": as_int(v_none),
        }
