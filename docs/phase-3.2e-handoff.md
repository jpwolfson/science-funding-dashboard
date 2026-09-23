# Phase 3.2e — NIH obligation accounts: running record

Status: in progress. Owner approval 2026-09-23 (option A of the scope memo):
onboard the 27 NIH federal accounts that Phase 3.2d deliberately left out
(`docs/phase-history.md`, Phase 3.2d entry) into the appropriations
obligation ledger. This supersedes the NIH descoping notes in
`docs/phase-3.2d-agency-roadmap.md` and `docs/phase-3.2d-execution-protocol.md`.

Cold-start rule: read `CLAUDE.md`, then this file top to bottom. The
"Next action" line is always current.

## Scope

27 resolved AAAS crosswalk accounts (all `resolved`; titles from
`reference/aaas_federal_account_crosswalk.json`):

| Account | Unit |
|---|---|
| `075-0807` | National Library of Medicine |
| `075-0819` | Fogarty International Center |
| `075-0837` | Advanced Research Projects Agency for Health (ARPA-H) |
| `075-0838` | NIH Buildings and Facilities |
| `075-0843` | National Institute on Aging |
| `075-0844` | NICHD |
| `075-0846` | NIH Office of the Director |
| `075-0849` | National Cancer Institute |
| `075-0851` | NIGMS |
| `075-0862` | NIEHS |
| `075-0872` | NHLBI |
| `075-0873` | NIDCR |
| `075-0875` | NCATS |
| `075-0884` | NIDDK |
| `075-0885` | NIAID |
| `075-0886` | NINDS |
| `075-0887` | National Eye Institute |
| `075-0888` | NIAMS |
| `075-0889` | NINR |
| `075-0890` | NIDCD |
| `075-0891` | NHGRI |
| `075-0892` | NIMH |
| `075-0893` | NIDA |
| `075-0894` | NIAAA |
| `075-0896` | NCCIH |
| `075-0897` | NIMHD |
| `075-0898` | NIBIB |

Measure semantics (decision layer a): NIH obligations are an account-level
measure, separate from and not additive to the NIH award ledger. No public
text reconciles the two; an internal cross-check is permitted.

## Step 1 — CI sizing (NCI `075-0849`)

Probe: `scripts/size_obligation_account.py` via
`.github/workflows/size-obligations.yml`, triggered by
`.github/triggers/size-obligations.json` on `claude/phase-3.2e-nih-sizing`.
It issues the production File B and File C requests (same columns as
`scripts/pull_obligation_account.py`) for FY2025 P12 and FY2026 P10, with a
5.5 h status cap instead of the adapter's 2 h, and commits
`reference/sizing/075-0849-FY*.json`.

Comparison point: the largest File C downloads already handled are USDA ARS
FY2024 (537,177 rows) and NSF R&RA FY2023 (520,830 rows).

Capacity baseline (scheduled weekly run 35626367929, 53 accounts): 106
serialized pull jobs, all green; median 16.7 min, p90 18.3, max 26.8 (DoD
Air Force FY2020); pulls sum 29.2 h; reconcile 23.5 min; wall clock 29.7 h
(Mon 16:33 → Tue 22:17 UTC). Job time is nearly flat across accounts of very
different size, so it is dominated by the fixed per-request cost (up to 11
File B period requests + 1 File C, each with a 20 s cooldown and a
generator queue wait), not by File C volume. Naive extrapolation: 27 NIH
accounts × 2 jobs × ~17 min ≈ +15 h/week, so ~45 h wall clock — past the
Tue ~23:00 UTC merge-quiet window. That holds only if NCI sizing confirms
NIH File C generation stays inside the flat regime.

Result: run
[`35925926839`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/35925926839),
both jobs green (reports: `reference/sizing/075-0849-FY2025P12.json`,
`reference/sizing/075-0849-FY2026P10.json`):

| NCI `075-0849` | FY2025 P12 | FY2026 P10 |
|---|---:|---:|
| File C generate + retrieve | 328 s | 279 s |
| File C ZIP | 72.2 MB | 57.4 MB |
| File C rows (assistance / contracts / unlinked) | 130,115 (112,280 / 17,294 / 541) | 90,479 (80,848 / 9,039 / 592) |
| Nonzero File C rows | 12,981 | 7,898 |
| Distinct awards / normalized events (est.) | 10,189 / 12,904 | 6,667 / 7,840 |
| Peak RSS (parse + shape) | 554 MB | 437 MB |
| File B P-final rows / generate | 58 / 21 s | 48 / 16 s |
| File B total (net obligations) | $7,423,092,042.18 | $4,644,703,508.38 |
| File C total | $5,593,663,121.91 (75.4% of B) | $3,060,834,916.60 (65.9% of B) |

Program Activities: FY2025 PAC/PAN `0001` "NATIONAL CANCER INSTITUTE
(0849)", `0801` "NIH REIMBURSABLE - OTHER", `0000` UNKNOWN/OTHER (zero
cents); FY2026 PARK-only, `5ZC7KSR3EPF` plus the `0000` zero row.

**Decision (engineering, recorded):** NIH's largest account is ~¼ of the
File C rows already handled routinely (NSF R&RA FY2023 520,830; USDA ARS
FY2024 537,177) and generates in ~5 min, far inside the adapter's 2 h cap.
The earlier cap hits (NIFA FY2019, IES FY2018) were source-queue stalls on
small accounts, not volume; W11/W13 already cover them. Therefore:
no File C partitioning, no special rotation, and the standard weekly plan
(current FY + one rotating historical FY per account). Cost: +54 serialized
jobs × ~16 min ≈ +14–15 h, taking the weekly run from ~30 h to ~44–45 h
(Mon 10:37 → ~Wed 07:00 UTC). Actions minutes on this public repo are not
billed, so this is not recurring spend. The operational effect is a longer
merge-quiet window; that is recorded in `CLAUDE.md` at closeout. Reconcile
(23.5 min today, 60 min timeout) grows with account count; its timeout is
raised in the registration PR.

## Step 2 — registry discovery (27 accounts)

`scripts/discover_obligation_program_activities.py` (same workflow, three
serial chunks) records per account × FY2017–FY2026: File B PA identities at
the final period, the federal-account record (incl.
`total_obligated_amount`, the pull's File A check), the first non-empty
period of the first active FY, and the official per-account PARK list.
Output: `reference/sizing/nih_registry_discovery_{1,2,3}.json`. These feed
registry entries and baseline scaffolds (NSF precedent: replaceable
`partial` rows without `obligationsCents`; the backfill pins them). The
backfill remains the fail-closed alias-drift gate.

## Log

| When (UTC) | Event | Result |
|---|---|---|
| 2026-09-23 22:01 | Sizing run 35925926839 | green; NCI small (above) |
| 2026-09-23 22:01 | Test run 35925926684 on probe commit | green (fast tier 9.5 min on CI) |
| 2026-09-23 | Discovery run (27 accounts) triggered | pending |

## Next action

Wait for the discovery run; read `reference/sizing/nih_registry_discovery_*.json`;
brief a Sonnet worker to author 27 registry entries + scaffold baselines +
`tests/test_obligations_nih.py` on `claude/phase-3.2e-nih-registry`.
