# Manual SEC Form N-PORT quarterly update

This is the only supported quarterly N-PORT update procedure. Do not download
SEC Archives or quarterly datasets from application code, CI, or Codex. Use
only the official quarterly ZIP supplied by the operator in the current chat.

## Preconditions

1. Start from the latest `main` and create a dedicated working branch.
2. Confirm the attachment came from the SEC Form N-PORT quarterly datasets
   page. Do not substitute mirrors or reconstruct a ZIP from individual files.
3. Keep the ZIP outside the repository. `*_nport.zip` is ignored as an
   additional safeguard.
4. Record the attachment path and expected quarter, but do not rename a file to
   make a failed quarter check pass.

## Run

From the repository root:

```bash
npm ci
npm run import:nport -- /absolute/path/YYYYqN_nport.zip
```

The import command must validate all of the following before updating data:

- filename matches the official `YYYYqN_nport.zip` pattern;
- the file is a non-empty, structurally valid ZIP;
- `SUBMISSION.tsv`, `FUND_REPORTED_INFO.tsv`,
  `FUND_REPORTED_HOLDING.tsv`, and `IDENTIFIERS.tsv` exist at the ZIP root;
- every required TSV header used by the parser is present;
- all submission filing dates belong to the filename quarter;
- at least one eligible ETF filing with usable US equity holdings is parsed.

The command prints the ZIP byte size and SHA-256 digest for the update record.

The ZIP itself is never copied into the repository. The command replaces the
selected quarter in the normalized filing snapshot, then runs:

```text
sync:universe
sync:atlas
sync:data
sync:oos
test
typecheck
lint
build
```

Success is indicated by:

```text
MANUAL_NPORT_IMPORT_OK quarter=YYYYqN filings=N
```

Absence of this marker is failure.

## Review before commit

Run `git status --short` and inspect the complete diff. The expected changes are
normalized N-PORT bootstrap data and generated Universe/atlas/market/OOS files.
The ZIP must not appear. Reject the update if strategy or selection source code
changed, including `src/lib/config.ts` or `src/lib/strategy/`.

Review the reported Top 80 additions/removals and the updated Top2. A large
Universe change must be explained from filing coverage, ETF eligibility, or
holding changes. Never tune Production parameters to make the result look more
familiar.

Confirm that Ranking, Top2, Universe, current dashboard state, and Forward OOS
share the newly generated as-of data. Review frozen Backtest files carefully;
the historical Backtest must not advance with OOS.

## Publish gate

Only when every validation passes:

1. commit the generated data and supporting audit output;
2. push the working branch;
3. open a PR;
4. wait for CI;
5. merge to `main` only after CI succeeds;
6. confirm the GitHub Pages deployment and displayed as-of date.

If any validation, consistency check, CI job, or visual check fails, do not
change `main`. Report the quarter, failure point, relevant counts, and retained
Production state.

## Completion report

Report:

- imported quarter;
- eligible N-PORT filing count;
- principal Top 80 additions and removals;
- updated Top2;
- test/typecheck/lint/build results;
- commit SHA;
- whether the change reached `main`.
