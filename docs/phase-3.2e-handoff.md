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
[`35925926839`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/35925926839)
pending.

## Log

| When (UTC) | Event | Result |
|---|---|---|
| 2026-09-23 | Sizing probe committed and triggered | pending |

## Next action

Wait for the sizing run; read `reference/sizing/075-0849-*.json`; decide the
partition and rotation plan.
