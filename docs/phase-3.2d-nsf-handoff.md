# Phase 3.2d NSF obligation-account handoff

Status: complete. PR
[#31](https://github.com/jpwolfson/science-funding-dashboard/pull/31)
merged four reconciled FY2017--FY2026 obligation stores, exact baselines,
dashboards, and combined sentinel coverage after the terminal CI backfill.

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

## Accepted exact baselines

Each account has a schema-v2 baseline. Before the first accepted build,
pullable years used replaceable `partial` rows without `obligationsCents`; that
made all 40 account-year partitions selectable by `--mode full` without
falsely publishing unverified pins. Atomic reconciliation replaced those
scaffolds with the accepted lifecycle state:

- FY2017 stays partial, with `firstPeriod: 6` and an exact P12 File B pin;
- FY2018–25 are promoted to complete exact-cent P12 pins; and
- FY2026 stays partial with an exact P09 pin.

The committed snapshot passes both identities: File C plus the residual equals
File B in every Program-Activity/reporting-period bucket, and annual File B
equals the accepted GTAS/File A pin exactly.

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
Those gates authorized the accepted first full backfill recorded below.

The trigger payload used was:

```json
{"mode":"full","accounts":"nsf","from_fy":"","to_fy":"","current_period":""}
```

The coordinator applied and later restored the trigger-file change; the worker
did not modify `.github/triggers/update-obligations.json`.

## Accepted release evidence

Durable run
[`31623021735`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/31623021735)
completed with 43 logical jobs: plan, all 40 account-year pulls, and reconcile
succeeded (42 successes); the branch-only deploy job was skipped as designed.
Reconcile job `94341025791` atomically committed snapshot
`12d829ef777a9931dba30a4bc93b50a77a710378`. The merge commit is
`689aba6a27f7f7282c444eacd583c4e694789bd7`.

All values below are integer cents. Every accepted account-year reconciles
canonical File B exactly to the corresponding File A pin, and every
PA/reporting-period grain reconciles File C plus its explicit residual to File
B. The 40 individual year pins remain enumerated in the four
`reference/nsf_*_obligation_baseline.json` files.

| Account | Years | File A = File B | File C | File B - File C |
|---|---:|---:|---:|---:|
| Research and Related Activities | 10 | 6,588,061,578,936 | 6,171,340,483,510 | 416,721,095,426 |
| STEM Education | 10 | 975,424,614,012 | 903,911,851,852 | 71,512,762,160 |
| Agency Operations and Award Management | 10 | 387,265,274,505 | 72,196,144,171 | 315,069,130,334 |
| Major Research Equipment and Facilities Construction | 10 | 219,198,099,019 | 198,817,658,033 | 20,380,440,986 |
| **Total** | **40** | **8,169,949,566,472** | **7,346,266,137,566** | **823,683,428,906** |

The accepted provenance contains 452 source-download snapshots with 2,749,284
parsed member rows, normalized to 291,110 signed events. Fail-closed Program
Activity resolution leaves zero unmapped identities, and obligation validation
completed with zero warnings. Overall File C/net is
`89.91813324911762%`; the residual remains explicit ledger activity.

The reconciled NSF subtree is 114,300,604 bytes. Its compressed event
partitions are 100,735,265 bytes and provenance records are 778,367 bytes.
The serialized run elapsed 10h44m55s; reconciliation ran 6m35s. Reconcile and
restored-head verification both passed fast 7/7 and rendered 3/3; the rendered
matrix covered five representative obligation cases, all 20 NSF-first
account/PA/theme cases, and both sentinel cases. Fresh light/dark reader review
and post-merge deploy/live spot checks were green.

The existing NSF award-ledger dashboards and data remain untouched regression
fixtures throughout this work.
