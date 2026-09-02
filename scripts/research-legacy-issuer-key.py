#!/usr/bin/env python3
from __future__ import annotations

import html
import re

TRAILING_FOOTNOTE = re.compile(r'\s*\((?:[A-Z]{1,3}|\d{1,3})\)\s*$', re.I)


def legacy_issuer_key(raw: str) -> str:
    """Conservative PIT identifier derived only from the filing description.

    Deliberately retains share-class and ADR/GDR/security-form tokens so distinct
    securities are not merged merely for coverage. No N-PX, prices, listing
    survival, or future data are consulted.
    """
    s = html.unescape(raw or '').upper().replace('&', ' AND ')
    while True:
        nxt = TRAILING_FOOTNOTE.sub('', s).strip()
        if nxt == s.strip():
            s = nxt
            break
        s = nxt
    s = re.sub(r'\b(INCORPORATED|INCORPORATION)\b', 'INC', s)
    s = re.sub(r'\bCORPORATION\b', 'CORP', s)
    s = re.sub(r'\bCOMPANY\b', 'CO', s)
    s = re.sub(r'\bLIMITED\b', 'LTD', s)
    s = re.sub(r'\bCOMPANIES\b', 'COS', s)
    # Leading article is formatting noise; security-form tokens remain.
    s = re.sub(r'^\s*THE\s+', '', s)
    return ' '.join(re.sub(r'[^A-Z0-9]+', ' ', s).split())


def self_test() -> None:
    assert legacy_issuer_key('The Acme Corporation (a)') == 'ACME CORP'
    assert legacy_issuer_key('Acme Corp. Class A') == 'ACME CORP CLASS A'
    assert legacy_issuer_key('Acme Corp. ADR') == 'ACME CORP ADR'
    assert legacy_issuer_key('Acme Corp. Class A') != legacy_issuer_key('Acme Corp. Class B')
    assert legacy_issuer_key('Acme Corp. ADR') != legacy_issuer_key('Acme Corp.')
    print('SELF_TEST_PASS')


if __name__ == '__main__':
    self_test()
