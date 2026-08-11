# Phase 3.2a handoff

Status: implementation complete. The obligation ledger is platformized for
registry-driven multi-account operation. The first branch workflow run replaces
the current DOE legacy-migration marker with accepted source provenance; later
weekly rotations replace the remaining historical markers without inventing
facts discarded by the Phase 3.1b pilot.

## Delivered contract

- Schema v2 is a hard migration. Every obligation dashboard and navigation
  index declares `schemaVersion: 2`; `fileCCoverage` was removed and replaced
  only by `fileCToNetRatio`.
- The registry owns each account's baseline path, availability start, reporting
  lag, and freshness SLA. The planner builds an account × FY matrix for weekly,
  full, and bounded custom runs.
- Weekly mode refreshes the newest source-available FY for every account and
  rotates one historical FY per account. P01 is not fabricated: before P02 is
  available, the prior P12 snapshot remains the newest refresh target.
- Each accepted partition commits request scope, source-status and parsed row
  counts, raw ZIP SHA-256 values, normalized event-content fingerprint,
  replacement lineage, and compact added/removed/changed diff hashes.
- Raw ZIPs have 14-day artifact retention; normalized account-year transfer
  artifacts have one-day retention. No external storage or standing download
  task is required.
- Reconciliation is fail-closed and global. Every matrix job must finish before
  one candidate snapshot updates baselines, rebuilds all account/agency/root
  pages, validates all accounts, and becomes both the Git commit and the exact
  Pages artifact.
- Obligation-only commits no longer rely on the generic push-triggered Pages
  workflow. The obligation workflow deploys its own already-validated artifact.
- A ten-day source freshness SLA is enforced in production. Missing required
  shards, legacy current provenance, stale manifests/dashboards, changed Program
  Activities, non-public links, and console/network/render failures stop
  publication.
- The headless Chrome matrix covers light/dark, 1440px/390px, empty current-FY,
  negative activity, and signed File C/net values outside 0–100%, while also
  checking native keyboard links and visible focus styling.

## Migration honesty

Phase 3.1b did not retain raw archive hashes, accepted request echoes, or status
row counts. The migration records those ten DOE partitions as
`legacy-migrated`, commits their normalized content and shard hashes, and says
explicitly that discarded source facts were not reconstructed. Production
freshness requires the current partition to be replaced by an accepted v2 pull.
The scheduled historical rotation then replaces one legacy year per week.

## Local release evidence

- 64 unit and contract tests pass.
- Obligation, NIH, and USAspending calibration validators pass offline.
- Python compilation and every registry/reference JSON parse pass.
- The five-case rendered Chrome matrix passes with no JavaScript, network,
  public-link, layout-state, or keyboard-contract failures.
- Existing `FY####.csv.gz` event shards are byte-unchanged by the migration.
