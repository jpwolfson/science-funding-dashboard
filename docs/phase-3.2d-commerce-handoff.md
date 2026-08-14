# Phase 3.2d Commerce staged scaffold handoff

Prepared 2026-08-12 on `agent/3-2d-commerce-staged`, based on authoritative
main `689aba6a27f7f7282c444eacd583c4e694789bd7`.

## Current stage: BEA FY2020 probe accepted

Only `commerce/bea` is registered in this first commit. No Commerce store,
download, trigger, workflow, remote branch, CI run, or pull request is created.
The account uses the official title **Salaries and Expenses, Economic and
Statistical Analysis**, federal account `013-1500`, and the complete reviewed
five-identity Program Activity inventory (four PAC/PAN rows plus one PARK row)
collapsed into four collision-safe canonical paths.

The official FY2020 federal-account snapshot and final Program Activity query
are empty, but the accepted custom download proves that the year contains real
within-year obligation and deobligation activity. File B is empty at P02,
material at P03 through P11, and empty again at P12. File C contains 143 rows.
The normalized partition contains 166 events: 143 File C events and 23 File B
residuals. Gross positive and negative obligations are each $105,061,446.13,
so the final net is exactly zero. The evidence-backed baseline row is:

```json
{"status":"complete","firstPeriod":3,"asOfPeriod":12,"obligationsCents":0}
```

This is a zero-net claim backed by real source events, not a synthetic empty
year. Durable hashes, row counts, request scopes, and the normalized event
fingerprint are recorded in
`reference/commerce_bea_fy2020_probe_evidence.json`. The accepted probe was:

```json
{
  "mode": "custom",
  "accounts": "commerce/bea",
  "from_fy": 2020,
  "to_fy": 2020,
  "current_period": 12
}
```

The old planned `unavailable` replacement is invalid and must not be applied.
The next authorized BEA operation is a full ten-year backfill so FY2020 lands
atomically with all other source-available BEA years.

## Planned append-only commit sequence

| Stage | Newly registered accounts | Commerce full-plan jobs | Readiness |
|---|---|---:|---|
| BEA accepted | BEA | 10 | all ten years pinned; full BEA backfill required |
| NOAA | NOAA ORF + NOAA PAC | 30 | only after atomic BEA data commit |
| NIST | NIST STRS + NIST ITS | 50 | only after atomic NOAA data commit |
| Statistics | Census Current | 60 | all registered years pinned |
| Census Periodic | Census Periodic | 70 | final seven-account scaffold |

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
