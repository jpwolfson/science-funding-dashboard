# Verification regime

> **GOVERNING PRINCIPLE (owner directive).** The verification regime is
> uniform across agencies. The verifier contains universal invariants only;
> every agency-specific fact is a declared parameter in that account's
> registry entry (`config/obligation_accounts.json`) or baseline file
> (`reference/*_obligation_baseline.json`) — one schema is the entire
> specialization surface. No agency-conditional code paths in any verifier.
> If an account needs something the schema cannot express, that is a schema
> extension landed once by the coordinator, never a code fork.

`scripts/verify.py` is the single entry point for that regime: one script,
four tiers, uniform exit codes (`0` pass, `1` fail, `2` usage error), and an
optional `--json <path>` machine-readable result. Every workflow in
`.github/workflows/` and every worker/coordinator in the Phase 3.2d protocol
runs the same commands documented here — there is exactly one source of
truth for "what does verification check," and it cannot drift between what
an agent runs locally and what CI runs, because they are the same command.

A contract test (`tests/test_verification_regime.py`) enforces the
governing principle mechanically: it derives the full slug list from
`config/obligation_accounts.json` at test time and fails if any of those
agency/account slugs appears as a string literal in `scripts/verify.py`,
`scripts/validate_obligations.py`, `scripts/validate_award_invariants.py`,
or `scripts/smoke_obligation_pages.py`. A newly onboarded agency is covered
automatically, with no edit to the test itself.

`scripts/validate_funding_sentinel.py` is deliberately **not** covered by
that contract test. Its DOE October 2025 announcement pins
(`doe-october-2025-portfolio-action` and the frozen amount/award/office
fields that go with it) hold one specific sourced *event's* structured
fields constant post-acceptance — a per-source content pin scoped to the
funding-action sentinel (Phase 3.2c), not an account-verification parameter.
Pinning one announcement's content is orthogonal to whether the obligation
verifier is agency-uniform; see the module docstring of
`scripts/validate_award_invariants.py` and the top of
`tests/test_verification_regime.py` for the same note in code.

## Tier table

| Tier | Cost (measured) | What it checks | Exit semantics |
|---|---|---|---|
| `registry` | ~0.01 s (10 checks, 1 account) | Pre-backfill lint of `config/obligation_accounts.json` + each account's baseline, against the specialization schema below. `--account <path>` lints one entry. | 0 pass / 1 fail / 2 usage |
| `fast` (default) | ~19 s | Full `unittest` suite + every existing offline validator (`validate_obligations.py --allow-empty`, `validate_nih.py`, `validate_usaspending_calibration.py`, `validate_funding_sentinel.py`, `verify_dms_baseline.py`) + `validate_award_invariants.py` (new: `totalAwards == Σfiscalyears == Σmonthly`, `fyCumulative` endpoints exact, `root == Σchildren`). | 0 pass / 1 fail / 2 usage |
| `rendered` | ~9 s | Existing headless-Chrome smoke matrices (`smoke_obligation_pages.py`, `smoke_sentinel_page.py`) **plus** `smoke_obligation_pages.py --all-accounts`, which renders every registered account page and one Program Activity sub-page per account, both themes, discovered from the registry — never a hardcoded path list. Zero console errors is part of every case. | 0 pass / 1 fail / 2 usage |
| `screens` | ~6 s (1 account today) | Reader-review screenshot pack: obligations landing, every account page, one Program Activity page per agency, the sentinel page, and the award root, light mode, 1100 px wide, full page, to `--out` (default OS temp dir). Prints the manifest. **Never pass/fails** — it is a release-bar input for a human/fresh-agent reader review (working regime item 5), not a mechanical gate. | always 0 (usage errors still exit 2) |

Costs above were measured on this branch with 1 registered obligation
account (DOE SC) and 132 award-ledger dashboards; they will grow with the
registry, and the ~60 s fast-tier target has substantial headroom.

### When workers/coordinator run each tier (Phase 3.2d protocol)

See the "Verification regime" section added to
`docs/phase-3.2d-execution-protocol.md` for the authoritative mapping; in
summary:

- **Worker:** `registry` before a backfill starts (catch a bad registry
  entry before spending API budget); `fast` after every local iteration;
  `fast` + `rendered` with the JSON result attached as PR evidence before
  opening the PR.
- **Coordinator:** `fast` + `rendered` on the merged tree after each serial
  merge, diffed against the worker's attached JSON to confirm nothing
  regressed.
- **Final release gates:** `rendered --all-accounts` (via `smoke_obligation_pages.py
  --all-accounts`, invoked by the `rendered` tier), `screens` (feeds the
  reader review), and the footprint figures folded into every JSON report.

## JSON result contract

`--json <path>` writes one object, `schemaVersion: 1`:

```jsonc
{
  "schemaVersion": 1,
  "tier": "fast",                 // "registry" | "fast" | "rendered" | "screens"
  "account": null,                // registry tier with --account: the account path; else null
  "generatedAt": "2026-08-12T15:07:26.074734+00:00",
  "durationSeconds": 18.873,
  "passed": true,                 // screens tier: always true
  "checks": [                     // absent on the screens tier (see "screens" below instead)
    {
      "name": "validate-nih",
      "passed": true,
      "evidence": "NIH validation passed: 28 units, 708233 unique awards", // one line
      "seconds": 7.377
    }
    // ...
  ],
  "screens": {                    // present only on the screens tier, in place of "checks"
    "outDir": "/tmp/verification-screens-20260812T150700Z",
    "manifest": [
      {"label": "obligations-landing", "orgPath": "obligations",
       "file": ".../obligations-landing.png", "note": "ok", "seconds": 1.1}
      // ...
    ]
  },
  "footprint": {
    "perTreeBytes": {"data": 80352642, "reference": 455405, "...": "..."},
    "totalTrackedBytes": 81484660,
    "gzippedStoreBytes": 39084835,   // committed *.gz store files under data/
    "pagesArtifact": {
      "fileCount": 1234,
      "totalBytes": 42000000,        // exact runtime artifact before tar packaging
      "status": "ok",                // ok | warning | stop
      "warningThresholdBytes": 850000000,
      "stopThresholdBytes": 950000000,
      "pagesLimitBytes": 1000000000,
      "headroomBytes": 958000000,
      "excludedFromArtifact": "data/obligations/**/events/*.csv.gz"
    },
    "trajectory": {                  // null if git history has no data/-touching commit
      "method": "linear extrapolation of the data/ tree's committed byte total "
                "from the first commit that touched data/ to HEAD, projected 52 weeks forward",
      "note": "the sampled history to date is dominated by one-time historical "
              "backfills, not steady-state weekly incremental refreshes, so this "
              "rate is a conservative UPPER BOUND, not a steady-state forecast; "
              "re-derive after several weeks of pure incremental refresh history exist",
      "firstDataCommit": "dc911f2...",
      "firstDataCommitDate": "2026-08-08T00:01:49+00:00",
      "weeksElapsed": 1.0,
      "currentDataTreeBytes": 80352642,
      "weeklyGrowthBytesUpperBound": 78677019,
      "projected52WeekBytesUpperBound": 4171557630,
      "thresholdBytes": 966367641,     // 0.9 GiB
      "approachesOneGigabyte": true
    }
  }
}
```

Each check's `evidence` is always the last non-empty line the underlying
script printed to stdout/stderr — its own pass message, or its own fail
message, so the JSON evidence is exactly what a human sees on the terminal.

Every Pages-producing workflow uses `scripts/assemble_pages_site.py`, which
copies all runtime JSON and the site shell while retaining normalized
obligation event CSV archives in Git only. The browser does not request those
audit shards. `scripts/check_pages_footprint.py` measures the assembled tree,
emits a GitHub Actions warning at 850,000,000 bytes, and fails before upload at
950,000,000 bytes, leaving 50 MB below GitHub Pages' 1 GB site limit. CI runs
the same assembly and gate before merge. Warning and stop states appear both
as workflow annotations and in the GitHub job summary; every displayed byte
count is measured from `_site`, never inferred from the repository tree.

Rendered smoke matrices serve `_site` produced by that assembler. Their link
gate resolves every relative link against the assembled tree, renders every
NSF division with an `awards.csv` download, and fails if any normalized
obligation event archive is Pages-relative. NSF award CSVs remain in Pages;
obligation event archives remain Git-only and any future public link to one
must use `github.com`.

## Specialization schema

This is the entire agency-specific parameter surface every verifier reads.
Nothing outside this table may vary by agency inside a verifier; a new fact
a verifier needs is a new column here, added once, not a per-agency branch.

### `config/obligation_accounts.json` — per-account registry entry

| Field | Meaning |
|---|---|
| `path` | Registry key and URL slug, e.g. `doe/sc`. Must match `^[a-z0-9]+(/[a-z0-9-]+)+$`; unique across the registry. |
| `name`, `abbrev`, `agency` | Display strings. |
| `federalAccount` | Canonical Treasury federal-account symbol, `AAA-BBBB`; unique across the registry. |
| `agencyIdentifier` | The 3-digit agency prefix of `federalAccount`; the registry tier checks they agree. |
| `adapter` | Which shared adapter module pulls this account (`usaspending_obligations` today). |
| `baseline` | Path to this account's baseline JSON (see below). |
| `availability.firstFiscalYear` / `firstFiscalYearPeriod` / `regularFirstPeriod` | Source-availability boundary: the first FY File B/C exist for this account, that FY's first reporting period, and the first period of every regular FY. |
| `programActivities[]` | `{slug, code, name, park?, parkAliases?, codeNameAliases?, abbrev?}` — canonical Program Activity identities. `slug` and canonical `(code, name)` must be unique; a source code may repeat when the agency reused it for distinct named activities. `park` is the preferred reporting key and `parkAliases` lists other PARK keys for the same identity. `codeNameAliases` lists exact historical `{code, name}` pairs for that identity. Every PARK and exact code/name token must map to exactly one identity. A nonblank PARK is authoritative and must resolve as a declared `park`/`parkAliases` token; it never falls through to PAC/PAN or the implicit unknown bucket. An ambiguous or unknown identity fails closed. |
| `freshnessMaxDays` (optional, else `refreshDefaults.freshnessMaxDays`) | Days a current-FY source snapshot may age before `--check-freshness` fails. |

### `reference/*_obligation_baseline.json` — per-account baseline file

| Field | Meaning |
|---|---|
| `schemaVersion` | Must be `2`. |
| `federalAccount` | Must match the registry entry's `federalAccount`. |
| `source` | Human-readable citation for the pinned figures (e.g. "USAspending federal account fiscal-year snapshots (GTAS/File A)"). Required non-empty. |
| `fiscalYears.<FY>.status` | `complete` (or `available`, accepted as a synonym) / `partial` / `unavailable` — the completeness state pinned for that fiscal year. |
| `fiscalYears.<FY>.obligationsCents` | The pinned GTAS/File A cents total (whole-FY for `complete`, as-of-period for `partial`). |
| `fiscalYears.<FY>.fileBObligationsCents` | Optional exact canonical File B cents total, used only when the official source exposes a documented File A/File B variance. Omit for ordinary exact-equality rows. |
| `fiscalYears.<FY>.fileAFileBVarianceCents` | Required with `fileBObligationsCents`; must equal `obligationsCents - fileBObligationsCents` exactly and must be non-zero. |
| `fiscalYears.<FY>.fileAFileBVarianceReason` | Required non-empty source disclosure when the dual-pin fields are present. |
| `fiscalYears.<FY>.firstPeriod` / `asOfPeriod` | For `partial` years: the first reporting period covered and the period the pin is as-of. |
| `fiscalYears.<FY>.reason` | Required for `unavailable` years — why no pin exists (e.g. "Files A/B/C begin in FY2017 Q2"). |

### `reference/aaas_federal_account_crosswalk.json` — reference-only, consulted by the registry tier

| Field | Meaning |
|---|---|
| `rows[].federal_accounts[].code` | Federal account code(s) an AAAS row maps to. The registry tier finds every row whose `federal_accounts` includes an account's `federalAccount`. |
| `rows[].status` | `resolved` / `provisional` / `unresolved`. Where corresponding rows exist, the registry tier requires at least one resolved mapping for the account. Separate provisional/unresolved alternate views referencing the same account are explicitly deferred and do not block its resolved mapping; an account with no corresponding row passes trivially (crosswalk coverage is not mandatory, per `docs/aaas-federal-account-crosswalk.md`). |

Award-ledger invariants (`validate_award_invariants.py`) read no
agency-specific parameter at all — `totalAwards`, `fiscalYears`, `monthly`,
`fyCumulative`, `children`, and `node.level` are schema fields every
award-ledger `dashboard.json` shares by construction, whichever source
produced it.

## Schema-extension rule

If a future account needs a fact none of the tables above can express, that
is a **schema extension**, landed once by the coordinator on `main` (or a
short-lived PR), with tests, before any worker depends on it — never a
per-agency `if` branch inside a verifier, and never a worker patching a
shared verifier on their own branch (the Phase 3.2d worker brief's
file-ownership contract already forbids this; this rule is the same policy
stated for verification specifically). Add the new field to this document's
specialization-schema tables in the same change.

## Recovering raw-artifact names from a legacy workflow rerun

GitHub reruns use the workflow definition and `GITHUB_SHA`/`GITHUB_REF` from
the original event. An obligation run started before raw audit archives gained
their `-attempt${{ github.run_attempt }}` suffix will therefore try to reuse an
attempt-1 raw artifact name when a failed matrix job is rerun. The normalized
partition name intentionally stays stable and is not part of this recovery.

Use `preserve-obligation-retry-artifacts.yml` only after the source workflow
run is terminal. Its input is a schema-v1 manifest pinning one run ID and each
raw artifact's exact ID, name, and `sha256:` digest. The recovery job:

1. rejects normalized/non-obligation names and an active source run;
2. re-fetches exact remote metadata, downloads every raw ZIP, and verifies its
   digest;
3. uploads the complete preservation bundle with fourteen-day retention; and
4. revalidates every local ZIP and remote record before deleting only those
   exact source artifacts.

Only after that recovery job succeeds may the source run's failed jobs be
rerun once. The empty trigger file is inert on `main`; a coordinator changes it
only on the dedicated `agent/3-2d-retry-artifact-operation` operational branch.
This path is solely for already-running legacy graphs. Newly dispatched runs
use attempt-specific raw names and need no cleanup.
