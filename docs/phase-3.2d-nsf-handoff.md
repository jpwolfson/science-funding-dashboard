# Phase 3.2d NSF obligation-account handoff

Status: registry and baseline scaffolds ready for the one-time CI backfill.
Generated obligation stores, exact-cent pins, rendered QA, and the pull request
remain gated on that backfill.

## Account disposition

All four NSF accounts in the reviewed Phase 3.2b crosswalk are `resolved` and
onboarded. No NSF account in the assigned wave-1 scope is parked.

| Path | Federal account | Official account title | Initial source window |
|---|---|---|---|
| `nsf/rra` | `049-0100` | Research and Related Activities, National Science Foundation | FY2017 P06–P12; FY2018 onward P02–P12; FY2026 currently through P09 |
| `nsf/stem-education` | `049-0106` | STEM Education, National Science Foundation | same |
| `nsf/aoam` | `049-0180` | Agency Operations and Award Management, National Science Foundation | same |
| `nsf/mrefc` | `049-0551` | Major Research Equipment and Facilities Construction, National Science Foundation | same |

The official title and account-symbol evidence is the USAspending federal
account record for
[`049-0100`](https://api.usaspending.gov/api/v2/federal_accounts/049-0100/),
[`049-0106`](https://api.usaspending.gov/api/v2/federal_accounts/049-0106/),
[`049-0180`](https://api.usaspending.gov/api/v2/federal_accounts/049-0180/), and
[`049-0551`](https://api.usaspending.gov/api/v2/federal_accounts/049-0551/),
reviewed 2026-08-12. Files A/B/C share the platform's established availability
boundary: FY2015–16 unavailable, FY2017 partial beginning P06, and FY2018 the
first full fiscal year. Award-search amounts are not used.

## Replaceable baseline scaffolds

Each account has a schema-v2 baseline. Pullable years are deliberately marked
`partial` without `obligationsCents` before the first accepted build. That makes
all 40 account-year partitions selectable by `--mode full` without falsely
publishing unverified pins. The atomic reconcile will replace those scaffolds:

- FY2017 stays partial, with `firstPeriod: 6` and an exact P12 File B pin;
- FY2018–25 are promoted to complete exact-cent P12 pins; and
- FY2026 stays partial with an exact P09 pin.

The reconcile candidate must pass both identities before any generated file or
pin is committed: File C plus the residual equals File B in every
Program-Activity/reporting-period bucket, and annual File B equals the accepted
GTAS/File A pin exactly.

## Program Activity alias review

The PAC/PAN history was reviewed from USAspending's `ref_program_activity`
records for agency `049`, main accounts `0100`, `0106`, `0180`, and `0551`,
budget years 2017–25. Current PARK values were independently reviewed through
the official per-account `program_activities` endpoints on 2026-08-12:

- [`049-0100`](https://api.usaspending.gov/api/v2/federal_accounts/049-0100/program_activities/?limit=100)
- [`049-0106`](https://api.usaspending.gov/api/v2/federal_accounts/049-0106/program_activities/?limit=100)
- [`049-0180`](https://api.usaspending.gov/api/v2/federal_accounts/049-0180/program_activities/?limit=100)
- [`049-0551`](https://api.usaspending.gov/api/v2/federal_accounts/049-0551/program_activities/?limit=100)

The reviewed canonical code sets are:

| Account | PAC/PAN codes retained | Current PARK-backed codes |
|---|---|---|
| R&RA | `0000`, `0001`, `0002`, `0003`, `0005`, `0006`, `0007`, `0008`, `0009`, `0010`, `0011`, `0013`, `0015`, `0016`, `00U1`, `00U2`, `0401`, `0402`, `0801` | all except `0000` and legacy `00U1` |
| STEM Education | `0000`, `0001`, `0302`, `0303`, `0401`, `0801` | `0001`, `0401`, `0801` |
| AOAM | `0000`, `0001`, `0401`, `0801` | `0001`, `0401`, `0801` |
| MREFC | `0000`, `0001`, `0401` | `0001`, `0401` |

Historical names are deliberately resolved by stable PAC/PAN code: for
example STEM Education code `0001` was formerly Education and Human Resources.
The current canonical label and PARK keep that series on one page. Unknown
attribution remains the visible `0000` bucket. A nonblank unregistered code or
PARK still fails closed during the backfill; the first CI run is therefore also
the final alias-drift gate against actual File B and File C archives.

## Pre-backfill verification and trigger

Pre-backfill results on commit candidate `agent/3-2d-nsf`:

- registry tier: 10/10 checks passed independently for `nsf/rra`,
  `nsf/stem-education`, `nsf/aoam`, and `nsf/mrefc`;
- NSF account contract tests: 4/4 passed; and
- fast tier: 7/7 checks passed in 9.8 seconds after rebasing onto main
  `4586584` (PRs #21–22 rebuild the sentinel atomically during obligation
  reconciliation and restrict published financial coverage to materialized
  live ledgers).

The worker reported the original integration defect to the coordinator and did
not modify shared reconciliation, sentinel, workflow, or validation code. The
uniform coordinator-owned fix is now present in this branch's main-line base.
The NSF registry is ready for its first full backfill.

The required trigger payload is:

```json
{"mode":"full","accounts":"nsf","from_fy":"","to_fy":"","current_period":""}
```

The coordinator owns the trigger-file change. The worker does not modify
`.github/triggers/update-obligations.json`.

## Post-backfill release checklist

- inspect all 40 accepted schema-v2 provenance records and exact baseline pins;
- confirm zero validator warnings and exact reconciliation for all four stores;
- run `python3 scripts/verify.py --tier fast --json ...`;
- run `python3 scripts/verify.py --tier rendered --json ...`;
- inspect representative NSF agency, account, and Program Activity pages in
  both light and dark themes, including signed/empty edge states;
- record event counts, fiscal-year cents, File C/net ratios, runtime, artifact
  growth, and any source corrections in this handoff; and
- open (but do not merge) the evidence-bearing pull request.

The existing NSF award-ledger dashboards and data remain untouched regression
fixtures throughout this work.
