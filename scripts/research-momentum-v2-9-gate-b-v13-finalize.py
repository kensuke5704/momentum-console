#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
BASE_OUT = R / "momentum-v2-9-final-gate-b-v10-h1-2006.json"
OUT = R / "momentum-v2-9-final-gate-b-v13-h1-2006.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    base = load("gate_b_v10_finalizer_base", ROOT / "scripts/research-momentum-v2-9-gate-b-v10-h1-2006.py")
    base.main()
    gate = json.loads(BASE_OUT.read_text())
    country = json.loads((R / "nq-hybrid-country-resolved-h1-2006.json").read_text())

    corp = gate["acceptedStructuralEvidence"]["transitionCorpBridge"]
    corp_bridge_pass = (
        int(corp.get("ecUsCount") or 0) > 0
        and int(corp.get("ecUsCorpCount") or 0) == int(corp.get("ecUsCount") or 0)
    )
    gate["historicalCorpBridgePolicy"] = (
        "Legacy 2006 filings have no N-PORT ISSUER_TYPE field. COMMON_EQUITY + conservative US is used as the "
        "historical equity analogue only under the frozen transition semantic validation that 226/226 EC+US "
        "holdings were CORP. This is an explicit legacy semantic bridge, not a claim that every 2006 issuer "
        "universally had a contemporaneous CORP code."
    )
    gate["historicalCorpBridgePass"] = corp_bridge_pass

    error_attempts = 0
    non_error_attempts = 0
    transport_only_unknown = []
    for row in country.get("resolutionAudit", []):
        filing_attempts = [
            f
            for attempt in row.get("attempts", [])
            for f in attempt.get("filingAttempts", [])
        ]
        errors = sum(bool(f.get("error")) for f in filing_attempts)
        non_errors = len(filing_attempts) - errors
        error_attempts += errors
        non_error_attempts += non_errors
        if row.get("classification") == "UNKNOWN" and filing_attempts and errors == len(filing_attempts):
            transport_only_unknown.append({
                "ticker": row.get("ticker"),
                "securityId": row.get("securityId"),
                "asOfReportDate": row.get("asOfReportDate"),
                "filingAttemptCount": len(filing_attempts),
            })
    gate["countryEvidenceTransportAudit"] = {
        "filingAttemptCount": error_attempts + non_error_attempts,
        "errorAttemptCount": error_attempts,
        "nonErrorAttemptCount": non_error_attempts,
        "transportOnlyUnknownIdentityDateCount": len(transport_only_unknown),
        "transportOnlyUnknownExamples": transport_only_unknown[:20],
        "policy": (
            "Transport-only UNKNOWN remains excluded from the primary Universe and is included in the existing "
            "mapped-UNKNOWN-to-US upper-bound sensitivity. Transport failures are quantified separately and are "
            "never promoted to US or otherwise imputed."
        ),
    }

    conflicts = list(gate.get("structuralConflicts") or [])
    if not corp_bridge_pass and "HISTORICAL_CORP_BRIDGE" not in conflicts:
        conflicts.append("HISTORICAL_CORP_BRIDGE")
    gate["structuralConflicts"] = conflicts
    gate["gateBPass"] = not conflicts
    gate["universeReconstructionConfirmed"] = not conflicts
    gate["purpose"] = (
        "Final return-independent Gate B v13 decision. Uses corrected rank correlation, frozen accepted transition "
        "evidence, explicit legacy CORP semantic bridge, corrected source-v6/holdings-v8, deterministic N-PX "
        "mapping, strict PIT country and conservative UNKNOWN upper-bound sensitivity."
    )
    OUT.write_text(json.dumps(gate, indent=2) + "\n")
    print(
        "GATE_B_V13",
        json.dumps({
            "gateBPass": gate["gateBPass"],
            "universeReconstructionConfirmed": gate["universeReconstructionConfirmed"],
            "structuralConflicts": conflicts,
            "historicalCorpBridgePass": corp_bridge_pass,
            "countryUpperBoundSensitivityStable": gate.get("countryUpperBoundSensitivityStable"),
            "countryEvidenceTransportAudit": gate["countryEvidenceTransportAudit"],
        }),
        flush=True,
    )
    if conflicts:
        raise SystemExit("Gate B v13 blockers: " + ",".join(conflicts))


if __name__ == "__main__":
    main()
