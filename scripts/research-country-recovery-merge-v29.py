#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "data/research"
COUNTRY = R / "nq-hybrid-country-resolved-h1-2006.json"
RECOVERY = R / "country-master-once-recovery-v29.json"
OUT = COUNTRY
ALLOWED_SOURCES = {"PIT_FOREIGN_PRIVATE_ISSUER_FORM", "PIT_FILING_DETAIL_ENTITY_STATE"}
FOREIGN_FORMS = {"6-K", "6-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}


def key(ticker, security_id, report_date):
    return ((ticker or "").strip().upper(), security_id or None, report_date or None)


def main() -> None:
    data = json.loads(COUNTRY.read_text())
    recovery = json.loads(RECOVERY.read_text())
    original = {key(r.get("ticker"), r.get("securityId"), r.get("asOfReportDate")): r for r in data.get("resolutionAudit", [])}
    promoted = {}
    for row in recovery.get("results", []):
        cls = row.get("classification")
        if cls not in {"US", "NON_US"}:
            continue
        source = row.get("resolutionSource")
        if source not in ALLOWED_SOURCES:
            raise RuntimeError(f"unapproved recovery source: {source}")
        if source == "PIT_FOREIGN_PRIVATE_ISSUER_FORM" and (cls != "NON_US" or row.get("evidenceForm") not in FOREIGN_FORMS):
            raise RuntimeError(f"invalid foreign-form recovery: {row}")
        if row.get("evidenceDateFiled") and row.get("asOfReportDate") and row["evidenceDateFiled"] > row["asOfReportDate"]:
            raise RuntimeError(f"future recovery evidence: {row}")
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        if k not in original or original[k].get("classification") != "UNKNOWN":
            raise RuntimeError(f"recovery may promote original UNKNOWN only: {k}")
        if k in promoted and promoted[k].get("classification") != cls:
            raise RuntimeError(f"conflicting recovery evidence: {k}")
        promoted[k] = row

    updated_audit = []
    for row in data.get("resolutionAudit", []):
        k = key(row.get("ticker"), row.get("securityId"), row.get("asOfReportDate"))
        evidence = promoted.get(k)
        if not evidence:
            updated_audit.append(row)
            continue
        nr = dict(row)
        nr.update({
            "classification": evidence["classification"],
            "stateCode": evidence.get("stateCode"),
            "resolutionSource": evidence.get("resolutionSource"),
            "evidenceForm": evidence.get("evidenceForm"),
            "evidenceDateFiled": evidence.get("evidenceDateFiled"),
            "evidenceFilename": evidence.get("evidenceFilename"),
            "recoveryEvidence": evidence,
        })
        updated_audit.append(nr)

    snapshots=[]; promoted_occurrences=0; promoted_weight=0.0
    for snapshot in data.get("monthSnapshots", []):
        mc=Counter(); mw=defaultdict(float); filings=[]
        for filing in snapshot.get("sourceFilings", []):
            fc=Counter(); fw=defaultdict(float); holdings=[]; report=filing.get("reportDate")
            for h0 in filing.get("holdings", []):
                h=dict(h0); cls=h.get("countryClassification") or "UNKNOWN"
                if h.get("mappingStatus")=="MATCHED_UNIQUE" and cls=="UNKNOWN":
                    evidence=promoted.get(key(h.get("mappedTicker"),h.get("mappedSecurityId"),report))
                    if evidence:
                        cls=evidence["classification"]
                        h["countryClassification"]=cls
                        h["countryReason"]=evidence["resolutionSource"]
                        h["countryResolutionEvidence"]=evidence
                        promoted_occurrences+=1; promoted_weight+=float(h.get("weight") or 0.0)
                w=float(h.get("weight") or 0.0); fc[cls]+=1; fw[cls]+=w; mc[cls]+=1; mw[cls]+=w; holdings.append(h)
            nf=dict(filing); nf["holdings"]=holdings; nf["countryClassificationCounts"]=dict(fc); nf["countryClassificationWeights"]=dict(fw); filings.append(nf)
        ns=dict(snapshot); ns["sourceFilings"]=filings; ns["countryClassificationCounts"]=dict(mc); ns["countryClassificationWeights"]=dict(mw); snapshots.append(ns)

    counts=Counter(r.get("classification") or "UNKNOWN" for r in updated_audit)
    out=dict(data); out["resolutionAudit"]=updated_audit; out["monthSnapshots"]=snapshots
    out["resolvedUSCount"]=counts["US"]; out["resolvedNonUSCount"]=counts["NON_US"]; out["remainingUnknownCount"]=counts["UNKNOWN"]
    out["countryEvidenceRule"]=str(data.get("countryEvidenceRule") or "")+" -> UNIFORM_PIT_RECOVERY[FOREIGN_PRIVATE_ISSUER_FORM_OR_EXPLICIT_FILING_DETAIL_STATE]"
    out["countryRecoveryAudit"]={
        "sourceRunId":34067495049,"sourceArtifactId":9999422941,"promotedIdentityDateCount":len(promoted),
        "promotedUSIdentityDateCount":sum(x["classification"]=="US" for x in promoted.values()),
        "promotedNonUSIdentityDateCount":sum(x["classification"]=="NON_US" for x in promoted.values()),
        "promotedHoldingOccurrenceCount":promoted_occurrences,"promotedHoldingWeightAcrossSnapshots":promoted_weight,
        "currentTickerFallbackAllowed":False,"allowedSources":sorted(ALLOWED_SOURCES),
        "policy":"Only original strict UNKNOWN exact identity/report-date keys are promoted by uniform return-independent PIT evidence; existing classifications are immutable."
    }
    OUT.write_text(json.dumps(out,indent=2)+"\n")
    print("COUNTRY_RECOVERY_MERGE",json.dumps(out["countryRecoveryAudit"]),flush=True)
    print("COUNTRY_RECOVERY_COUNTS",json.dumps({"US":counts["US"],"NON_US":counts["NON_US"],"UNKNOWN":counts["UNKNOWN"]}),flush=True)

if __name__=="__main__": main()
