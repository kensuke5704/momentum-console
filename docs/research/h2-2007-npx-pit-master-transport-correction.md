# H2 2007 N-PX PIT Master Transport Correction

Defined: 2026-09-08 JST after run `34189609394` failed before reading any 2007 N-PX inventory row and before any H2-2007 N-PX source-selection, security-master, or structural-mapping result was produced.

Run `34189609394` failed on the first 2007 QTR1 SEC index fetch. The frozen parser helper attempted direct `master.idx` and a `r.jina.ai` transport; the runner received HTTP 403 and HTTP 422 respectively. No N-PX inventory, selected-source set, parsed security record, or mapping result was observed.

This correction changes transport only. The validation definition in `docs/research/h2-2007-npx-pit-master-validation-definition.md` and every source-selection/PIT rule remain unchanged.

## Corrected transport

Use the official SEC quarterly `master.zip`, extract its embedded `master.idx`, and pass the resulting text into the already-defined H2-2007 inventory logic. This is the same official SEC full-index ZIP transport already used successfully by the validated cumulative N-Q inventory implementation `scripts/research-sec-marketwide-nq-inventory-through-h2-2007.py`.

The corrected wrapper must:

- request only the official `https://www.sec.gov/Archives/edgar/full-index/2007/QTR{q}/master.zip` resource;
- extract a member ending in `master.idx`;
- validate the extracted text with the frozen parser helper's existing `plausible_index()` check;
- leave the frozen N-PX record parser, issuer normalizer, 64-position sampling rule, fixed broad-family CIK set, signal dates, monotone admission rule, and all PIT assertions unchanged.

No fallback source may be chosen after observing mapping coverage. Failure of the official ZIP transport remains a stop condition.
