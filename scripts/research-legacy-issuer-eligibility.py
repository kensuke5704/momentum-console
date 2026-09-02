#!/usr/bin/env python3
from __future__ import annotations

import re

GENERIC_KEYS = {
    'INC','CORP','CO','LTD','CO LTD','INC LTD','PLC','AG','NV','SA','SPA','BV',
    'GROUP INC','HOLDINGS INC','HOLDING CO','HOLDINGS LTD'
}
NON_EQUITY = re.compile(
    r'\b(?:MONEY MARKET|LENDING PRIME|RESERVES? FUND|CASH|SHORT[ -]TERM|'
    r'REPURCHASE|TREASURY (?:BILL|NOTE|BOND)|COMMERCIAL PAPER|CERTIFICATE OF DEPOSIT|'
    r'PREFERRED|PREF(?:ERRED)? STOCK|NOTE DUE|NOTES DUE|BOND DUE|BONDS DUE|'
    r'WARRANTS?|RIGHTS?|OPTIONS?|FUTURES?|SWAPS?)\b', re.I
)
NON_US_PROXY = re.compile(r'\b(?:ADR|GDR|DEPOSITARY RECEIPT|DEPOSITORY RECEIPT)\b', re.I)
NON_CORP_PROXY = re.compile(r'\b(?:LIMITED PARTNERSHIP|L\.P\.|\bLP\b|L\.L\.C\.|\bLLC\b)\b', re.I)
HEADER_OR_TOTAL = re.compile(r'^(?:TOTAL|NET ASSETS?|SECURITY|DESCRIPTION|SHARES?|VALUE|MARKET VALUE)\b', re.I)


def classify(description: str, issuer_key: str) -> str:
    desc=' '.join((description or '').split())
    key=' '.join((issuer_key or '').split()).upper()
    if not key or key in GENERIC_KEYS or len(key) < 4:
        return 'GENERIC_FRAGMENT'
    if HEADER_OR_TOTAL.search(desc):
        return 'PARSER_ARTIFACT'
    if NON_EQUITY.search(desc):
        return 'NON_EC_PROXY'
    if NON_US_PROXY.search(desc):
        return 'NON_US_PROXY'
    if NON_CORP_PROXY.search(desc):
        return 'NON_CORP_PROXY'
    return 'LEGACY_EQUITY_CANDIDATE'


def eligible(description: str, issuer_key: str) -> bool:
    return classify(description, issuer_key) == 'LEGACY_EQUITY_CANDIDATE'


def self_test() -> None:
    assert classify('Inc. (a)','INC') == 'GENERIC_FRAGMENT'
    assert classify('Co., Ltd.','CO LTD') == 'GENERIC_FRAGMENT'
    assert classify('SSgA Prime Money Market Fund','SSGA PRIME MONEY MARKET FUND') == 'NON_EC_PROXY'
    assert classify('Lending Prime Portfolio (c)','LENDING PRIME PORTFOLIO') == 'NON_EC_PROXY'
    assert classify('Acme Corp. ADR','ACME CORP ADR') == 'NON_US_PROXY'
    assert classify('Pipeline Partners, L.P.','PIPELINE PARTNERS L P') == 'NON_CORP_PROXY'
    assert eligible('Exxon Mobil Corp.','EXXON MOBIL CORP')
    print('SELF_TEST_PASS')

if __name__=='__main__': self_test()
