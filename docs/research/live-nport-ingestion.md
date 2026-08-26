# Live SEC N-PORT ingestion research

This path evaluates individual EDGAR filings as a point-in-time overlay on the
quarterly N-PORT dataset. It does not change the Production strategy rules or
publish a Universe automatically.

## Confirmed constraint

GitHub-hosted Ubuntu and macOS runners receive HTTP 403 from both the SEC daily
index and individual filing documents. The current local development host was
also probed and returned the same HTTP 403 response. The response identifies
the request as an undeclared automated tool. A successful quarterly-only
rebuild is not proof that live ingestion worked. The GitHub-hosted research
workflows are therefore manual-only and are not Production update paths.

## Fail-closed contract

The live snapshot is accepted only when all of the following are true:

- at least one scanned daily index was available;
- at least one NPORT-P filing was discovered;
- every discovered accession was parsed or already present in the prior live
  snapshot;
- no parse failure remains;
- the snapshot reaches the required scan end date.

The snapshot is written through a temporary file and renamed only after these
checks pass. A failed run therefore leaves the previous validated snapshot
unchanged. `REQUIRE_LIVE_NPORT=1` prevents `build-universe.ts` from silently
falling back to the quarterly baseline.

## External runner validation

Register a runner that has confirmed SEC Archives access with both labels:

```text
self-hosted
sec-edgar
```

Then dispatch `Research Live N-PORT Self-hosted` with an explicit scan start and
end date. The job runs this sequence:

```text
SEC endpoint probe
quarterly baseline build
individual filing ingestion
validated quarterly + live merge
Top 80 audit
research artifact upload
```

The endpoint probe exits non-zero for HTTP 403, unexpected content, or network
failure. The workflow has no schedule and no write permission while access and
historical parity remain unproven.

## Candidate monthly timing

After several successful manual runs and historical parity checks, the safe
candidate is around `07:00 UTC` on days 1–4 of each month. This allows the SEC
overnight daily index to appear while leaving time before the next US session
open. Do not reuse the current `22:35 UTC` monthly timing for this live route.

## Promotion gates

Before any main-branch or Production integration:

1. SEC daily index and `primary_doc.xml` both succeed from the chosen runtime.
2. A validated live snapshot contains non-zero discovered filings.
3. Historical closed months reproduce the quarterly-dataset Universe within
   the accepted parity threshold.
4. Parse failures and zero discovery demonstrably preserve the previous
   Universe artifacts.
5. The job is repeatable across multiple month ends.
