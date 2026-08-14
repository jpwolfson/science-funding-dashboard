# Phase 3.2d Commerce staged scaffold handoff

Prepared 2026-08-12 on `agent/3-2d-commerce-staged`, based on authoritative
main `689aba6a27f7f7282c444eacd583c4e694789bd7`.

## Current stage: BEA FY2020 preflight

Only `commerce/bea` is registered in this first commit. No Commerce store,
download, trigger, workflow, remote branch, CI run, or pull request is created.
The account uses the official title **Salaries and Expenses, Economic and
Statistical Analysis**, federal account `013-1500`, and the complete reviewed
five-identity Program Activity inventory (four PAC/PAN rows plus one PARK row)
collapsed into four collision-safe canonical paths.

The official FY2020 federal-account snapshot and final Program Activity query
are empty, but that does not prove a genuinely empty custom File B/File C
download. The temporary baseline therefore marks FY2020 as source-available
and pinless at P12:

```json
{"status":"partial","firstPeriod":2,"asOfPeriod":12}
```

This is a probe state, not a zero-dollar claim. Tests require the planner to
select exactly this one custom job and fail a full-plan readiness check because
FY2020 has no `obligationsCents` pin. The only authorized preflight payload is:

```json
{
  "mode": "custom",
  "accounts": "commerce/bea",
  "from_fy": 2020,
  "to_fy": 2020,
  "current_period": 12
}
```

If every P02–P12 File B snapshot and P12 File C result is source-empty, the
later BEA/Census Current stage replaces this temporary row with the brief's
explicit unavailable row and retains no zero shard, zero provenance, or zero
pin. Any File A/File B amount, or File C activity without a File B anchor,
stops the sequence for diagnosis.

## Planned append-only commit sequence

| Stage | Newly registered accounts | Commerce full-plan jobs | Readiness |
|---|---|---:|---|
| BEA probe | BEA | 10 | blocked except the one FY2020/P12 custom probe |
| NOAA | NOAA ORF + NOAA PAC | 30 | NOAA batch ready; BEA remains probe-only |
| NIST | NIST STRS + NIST ITS | 50 | NIST batch ready; BEA remains probe-only |
| Statistics | final BEA gap + Census Current | 59 | all registered years pinned |
| Census Periodic | Census Periodic | 69 | final seven-account scaffold |

Every stage is required to pass its own account registry checks, the whole
registry tier, Commerce tests, the exact planner-count assertion, and the fast
tier with absent Commerce stores allowed. Only the coordinator may later add a
trigger commit or launch CI.

## Official evidence

- Account title: `https://api.usaspending.gov/api/v2/federal_accounts/013-1500/`
- Historical Program Activities:
  `https://api.usaspending.gov/api/v2/federal_accounts/013-1500/program_activities/?limit=100`
- Fiscal-year snapshots:
  `https://api.usaspending.gov/api/v2/federal_accounts/3693/fiscal_year_snapshot/{fiscal_year}/`
- Commerce source boundary:
  `https://api.usaspending.gov/api/v2/reporting/agencies/013/overview/?limit=100`

Files A/B/C begin at FY2017 P06. FY2015–16 are unavailable, FY2017 is
partial through P12, FY2018–19 and FY2021–25 are complete, and FY2026 is a
mutable P09 partial pin. All exact non-probe cent pins are preserved from the
reviewed Commerce execution brief.
