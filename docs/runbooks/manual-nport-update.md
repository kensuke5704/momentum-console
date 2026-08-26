# Manual N-PORT quarterly update

Use this runbook when the operator downloads the official SEC Form N-PORT quarterly ZIP manually and attaches or otherwise provides the local ZIP to Codex.

## Non-negotiable rules

- Do not change `src/lib/config.ts`, Production strategy parameters, momentum rules, risk rules, execution rules, or allocation rules as part of this task.
- Do not fetch the SEC ZIP from GitHub Actions or Vercel. The operator supplies the ZIP manually.
- Do not commit the ZIP itself to the repository.
- Fail closed. If validation, import, Universe generation, tests, typecheck, lint, or build fails, do not commit or push generated data.
- If the quarter already exists in `data/sec-nport/filings.json`, stop and report it. Do not overwrite an audited quarter automatically.
- Review the resulting diff before committing. Unexpected large Universe changes must be reported and investigated before push.

## Required operator input

One official SEC quarterly ZIP named so the quarter can be identified, for example:

```text
2026q3_nport.zip
```

The ZIP must contain at least:

```text
SUBMISSION.tsv
FUND_REPORTED_INFO.tsv
FUND_REPORTED_HOLDING.tsv
IDENTIFIERS.tsv
```

## Standard command

From the repository root:

```bash
npm ci
npm run import:nport -- /absolute/path/to/2026q3_nport.zip
```

`import:nport` performs the following sequence:

1. validates the ZIP filename, size, required tables, and table headers;
2. rejects an already-imported quarter;
3. copies the ZIP only to a temporary local cache;
4. runs `sync:sec` against that cache without requiring SEC network access;
5. confirms the quarter was recorded in `data/sec-nport/filings.json`;
6. rebuilds the Dynamic Universe;
7. refreshes atlas/data/OOS outputs;
8. runs the full `check` suite: tests, typecheck, lint, and build;
9. deletes the temporary ZIP cache;
10. never commits or pushes automatically.

A successful command ends with:

```text
MANUAL_NPORT_IMPORT_OK quarter=YYYYqN
```

## Post-import review

Before committing, inspect at least:

```bash
git status --short
git diff --stat
git diff -- data/sec-nport/filings.json public/data/universe-current.json public/data/universe-history.json
```

Confirm:

- the expected quarter is present;
- the latest Universe month is correct;
- Universe is non-empty and capped at 80;
- there is no unexpected strategy/config change;
- no ZIP or temporary file is staged;
- generated Top2/ranking/output files are internally consistent;
- `npm run check` has passed.

If the Universe changes materially, summarize added/removed symbols and verify the change is explainable by the new quarterly N-PORT data. Do not optimize or modify strategy parameters in response to the change.

## Commit/push policy

Only after all checks pass:

1. stage only the intended generated/code documentation files;
2. commit with a message such as `Update N-PORT data for 2026 Q3`;
3. push the working branch;
4. if the task is intended for Production, open/review a PR and ensure CI is green before merging to `main`;
5. report the imported quarter, Universe changes, current Top2, validation result, commit SHA, and whether main was updated.

If any check fails, leave Production/main unchanged and report the failure plus the files affected.
