#!/usr/bin/env python3
from __future__ import annotations

import re
from collections.abc import Callable

# Common presentation abbreviations observed in SEC issuer-name fields. These are
# lexical expansions only; downstream acceptance must still require that an alias
# resolves to exactly one ticker within the same SEC series snapshot.
ABBREVIATIONS = {
    'INTL': 'INTERNATIONAL',
    'WASH': 'WASHINGTON',
    'WORLDW': 'WORLDWIDE',
    'EXPEDTRS': 'EXPEDITORS',
    'TRANSN': 'TRANSPORTATION',
    'FGHT': 'FREIGHT',
    'TECH': 'TECHNOLOGY',
    'TECHNOLO': 'TECHNOLOGY',
    'HLDGS': 'HOLDINGS',
}
LEGAL_SUFFIXES = {'INC', 'CORP', 'CO', 'LTD', 'PLC', 'LLC', 'CORPORATION', 'COMPANY', 'INCORPORATED', 'LIMITED'}


def _expand_tokens(value: str) -> str:
    return ' '.join(ABBREVIATIONS.get(t, t) for t in value.split())


def _singular_tokens(value: str) -> str:
    out = []
    for token in value.split():
        if len(token) > 4 and token.endswith('S') and token not in {'HOLDINGS'}:
            out.append(token[:-1])
        else:
            out.append(token)
    return ' '.join(out)


def _truncated_prefixes(value: str) -> list[str]:
    """Model fixed-width SEC display truncation without fuzzy matching.

    Generate only lexical prefixes after dropping trailing legal/descriptive
    tokens. Downstream uniqueness is mandatory, so a short prefix cannot create
    an accepted mapping when multiple symbols share it in the same series.
    """
    tokens = value.split()
    out: list[str] = []
    for keep in range(len(tokens), 1, -1):
        prefix = tokens[:keep]
        last = prefix[-1]
        if len(last) >= 7:
            for n in range(len(last) - 1, max(5, len(last) - 6) - 1, -1):
                out.append(' '.join(prefix[:-1] + [last[:n]]))
        if keep < len(tokens):
            out.append(' '.join(prefix))
    return out


def issuer_aliases(raw: str, norm_issuer: Callable[[str], str]) -> list[str]:
    s = str(raw or '').strip()
    while True:
        stripped = re.sub(r'\s*\((?:[a-z]{1,3}|\d{1,3})\)\s*$', '', s, flags=re.I)
        if stripped == s:
            break
        s = stripped.strip()
    s = re.sub(r'\s*\(\s*CLASS\s+[A-Z0-9.-]+\s*\)\s*', ' ', s, flags=re.I)
    s = re.sub(r'[, ]+CLASS\s+[A-Z0-9.-]+\s*$', '', s, flags=re.I)
    s = re.sub(r'\s+(?:ADR|GDR)(?:\s*\*+)?\s*$', '', s, flags=re.I)
    s = re.sub(r'\s+\*+\s*$', '', s)
    base = norm_issuer(s)
    if not base:
        return []

    seeds = [base]
    no_the = ' '.join(t for t in base.split() if t != 'THE')
    if no_the:
        seeds.extend([no_the, f'THE {no_the}', f'{no_the} THE'])

    values: list[str] = []
    for seed in list(seeds):
        values.extend([seed, _expand_tokens(seed), _singular_tokens(seed), _singular_tokens(_expand_tokens(seed))])

    # Remove one legal suffix at a time. Production-side names often use a short
    # legal form while shareholder reports use the long form (or vice versa).
    for value in list(values):
        toks = value.split()
        if toks and toks[-1] in LEGAL_SUFFIXES:
            values.append(' '.join(toks[:-1]))
        values.append(re.sub(r'\bCOS\b', 'COMPANIES', value))
        values.append(re.sub(r'\bCOMPANIES\b', 'COS', value))
        values.append(re.sub(r'\bBANCORPORATION\b', 'BANCORP', value))
        values.append(re.sub(r'\bBANCORP\b', 'BANCORPORATION', value))

    # Apply common SEC fixed-width/truncated display forms to every lexical alias.
    for value in list(values):
        values.extend(_truncated_prefixes(value))

    # Space-insensitive aliases cover punctuation/initial presentation only:
    # J.M. vs JM, D.R. vs DR, UnitedHealth vs United Health, L3Harris vs L3 Harris.
    for value in list(values):
        compact = value.replace(' ', '')
        if len(compact) >= 5:
            values.append(compact)

    out: list[str] = []
    for value in values:
        value = ' '.join(value.split())
        if value and value not in out:
            out.append(value)
    return out
