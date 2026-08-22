# Phase 3.2d DOE handoff

## Scope and status

PR [#32](https://github.com/jpwolfson/science-funding-dashboard/pull/32)
onboarded the ten crosswalk-resolved DOE accounts in roadmap 3.2d-1A and
3.2d-1B. DOE Office of Science (`089-0222`, `doe/sc`) remains the Phase 3.1b
regression fixture. No account is parked. The worker-owned implementation did
not modify shared adapters, validators, workflows, site, sentinel, or trigger
files.

The registry, official-title review, Program Activity inventory, accepted
FY2017--FY2026 stores, exact-cent baselines, dashboards, rendered evidence,
and measured runtime/footprint record are complete. Source-specific
discoveries made during the serialized backfill are retained below.

## Official account evidence

Account titles and Program Activity inventories were read from USAspending's
official federal-account endpoints for FY2026. The inventory count is the raw
endpoint count across PAC/PAN and PARK rows; the normalized count is the unique
published identities after reviewed aliases and duplicate historical labels.

| Account | Path | Official account title | Bureau | Inventory | Normalized | Status |
|---|---|---|---|---:|---:|---|
| `089-0337` | `doe/arpa-e` | Advanced Research Projects Agency-Energy, Energy Programs, Energy | Energy Programs | 7 | 4 | live: 10 years |
| `089-0321` | `doe/eere` | Energy Efficiency and Renewable Energy, Energy Programs, Energy | Energy Programs | 32 | 26 | live: 10 years |
| `089-2297` | `doe/oced` | Clean Energy Demonstrations, Energy Programs, Energy | Energy Programs | 33 | 16 | live: 5 years |
| `089-0213` | `doe/fossil-energy` | Fossil Energy, Energy Programs, Energy | Energy Programs | 52 | 27 | live: 10 years |
| `089-0318` | `doe/electricity` | Electricity, Energy Programs, Energy | Energy Programs | 29 | 19 | live: 10 years |
| `089-2250` | `doe/ceser` | Cybersecurity, Energy Security, and Emergency Response, Energy Programs, Energy | Energy Programs | 14 | 11 | live: 8 years |
| `089-0319` | `doe/nuclear-energy` | Nuclear Energy, Energy Programs, Energy | Energy Programs | 58 | 29 | live: 10 years |
| `089-0240` | `doe/nnsa-weapons-activities` | Weapons Activities, National Nuclear Security Administration, Energy | National Nuclear Security Administration | 34 | 29 | live: 10 years |
| `089-0309` | `doe/nnsa-defense-nuclear-nonproliferation` | Defense Nuclear Nonproliferation, National Nuclear Security Administration, Energy | National Nuclear Security Administration | 18 | 16 | live: 10 years |
| `089-0216` | `doe/eia` | Energy Information Administration, Energy Programs, Energy | Energy Programs | 7 | 3 | live: 10 years |

Source URL pattern:

- account: `https://api.usaspending.gov/api/v2/federal_accounts/<account>/?fiscal_year=2026`
- Program Activities: `https://api.usaspending.gov/api/v2/federal_accounts/<account>/program_activities/`

Every corresponding Phase 3.2b AAAS row is `resolved`; the registry tier
confirmed this independently for all ten accounts.

The serialized backfill additionally exposed one official transient File B
identity that the current all-history inventory no longer lists: CESER FY2023
P06 contains PAC `0013`, `DCEI ENERGY MISSION ASSURANCE`. DOE's FY2023 budget
justification documents the transfer of this program from Electricity to
CESER. It therefore remains a first-class CESER identity rather than being
folded into Electricity or the unknown bucket. The branch registry and alias
tests include the exact pair.

The FY2026 P02-P07 custom File B snapshots use earlier PARK keys that the
FY2026 P08-P09 snapshots replace with consolidated/current keys. The official
Data Broker PARK mapping file at
`https://files.usaspending.gov/reference_data/park.csv` maps those earlier
keys exactly: `5Q0QFJ08DGM` to Cybersecurity for Energy Delivery Systems,
`5UWQ6UKQ7PC` to Risk Management Technology and Tools (CEDS),
`5Q0QFJ08DGW` to Infrastructure Security and Energy Restoration,
`5UWQ6UKQ7PN` to Response and Restoration, `5UWQ6UKQ7PZ` to Information
Sharing, Partnerships and Exercises, and `5WKQ40G9H6B` to CESER,
Infrastructure Investment and Jobs Act. Literal PARK `0000` appears only on a
zero-dollar P02 row and remains the explicit Unknown / other identity. These
are declared PARK aliases, not inferred dollar-based mappings.

## Program Activity alias review

The registry retains every unique PAC/PAN code returned by the official
inventory plus the visible `0000` unknown bucket. A PARK is attached to a
legacy code only when the official inventory provides an unambiguous
normalized-name relationship. Reused legacy codes and PARKs without a unique
predecessor remain first-class PARK-native identities; they are not silently
forced into an older program. This is why the normalized count can exceed the
unique PAC/PAN-code count.

Nine PARK-native identities remain deliberately separate:

| Account | PARK | Official name | Reason |
|---|---|---|---|
| EERE | `5WKQ3U7VKXN` | Infrastructure Investment and Jobs Act | legacy label differs and was not assumed equivalent |
| EERE | `63YPT7SFFAZ` | Energy Efficiency and Renewable Energy | account-wide PARK has no single legacy program predecessor |
| Fossil Energy | `5UWQ6Q4BYMT` | Mineral Sustainability | no legacy code with the same official identity |
| Fossil Energy | `5ZCQYAMAF08` | Natural Gas Technologies | legacy code `0020` is also used for Inflation Reduction Act; merging would be false |
| Electricity | `63YPT7S7RDC` | Electricity Programs | account-wide PARK has no single legacy program predecessor |
| CESER | `63YPTC2RBEP` | CESER Programs | account-wide PARK has no single legacy program predecessor |
| CESER | `63YPTC2RBF1` | Infrastructure Investment and Jobs Act | no one-to-one legacy identity was assumed |
| Nuclear Energy | `63YPT7SACCH` | Inflation Reduction Act | no unique legacy predecessor |
| Defense Nuclear Nonproliferation | `608PP9VRRFG` | Ukraine Supplemental | no legacy predecessor |

The NNSA boundary is explicit and tested. Weapons Activities maps direct work
to `5UWPV21LNPR` and retains the Weapons Activities program family under
`089-0240`. Defense Nuclear Nonproliferation maps direct work to
`5UWPV26R8KX` and retains its R&D/nonproliferation family under `089-0309`.
The AAAS NNSA RDT&E total remains a many-account alternate view; neither
account is relabeled as the aggregate.

## Source availability and baseline scaffolds

The ledger-wide File A/B/C boundary applies to every account:

- FY2015–16: source-unavailable, never synthesized;
- FY2017: partial history beginning at P06 and ending at P12;
- FY2018–25: full-year P12 targets;
- FY2026: partial through P09 at onboarding time.

Each source-available FY is represented by a replaceable `partial` scaffold so
`mode=full` plans the complete FY2017–26 history. The pull's accepted
provenance supplies `baselinePin`; atomic reconciliation upgrades FY2018–25 to
`complete` and fills exact File A cents for every source-available year before
anything is published. The DOE tests fail if a materialized store retains an
unfilled scaffold.

## Pre-backfill evidence

- Registry tier: `PASS`, 10/10 checks for each new account and 80/80 across
  the full 11-account registry.
- Full planner: 100 account-year jobs, ten per account, FY2017–26.
- New normalized identities: 180 across ten accounts.
- Office of Science: not part of the trigger selection and unchanged locally.
- Shared-code dependency: inherited main `4586584`, which truthfully limits
  sentinel financial coverage to materialized ledgers and keeps scaffold-only
  worker branches green; PR #21 still expands coverage inside atomic reconcile.
- Parked accounts: none.
- Pre-backfill fast tier: `PASS`, 7/7 checks in 10.0 seconds on inherited
  main `4586584`.

Exact trigger payload requested from the coordinator after the branch is
published:

```json
{
  "mode": "full",
  "accounts": "doe/arpa-e,doe/eere,doe/oced,doe/fossil-energy,doe/electricity,doe/ceser,doe/nuclear-energy,doe/nnsa-weapons-activities,doe/nnsa-defense-nuclear-nonproliferation,doe/eia",
  "from_fy": null,
  "to_fy": null,
  "current_period": null
}
```

## Post-backfill release evidence

The live Wave 1 backfill exposed a transient FY2021 P11 Fossil Energy File B
row `0020 / LEGACY MANAGEMENT` at exactly zero cents. The same accepted P11
snapshot simultaneously carries material `0020 / NATURAL GAS TECHNOLOGIES`
activity, while later source history reuses `0020` for Inflation Reduction Act.
Official final FY2021 totals and the all-history account inventory omit Legacy
Management, and the current PARK reference contains no `089-0213` successor
(same-name PARK rows belong to different DOE accounts). The registry therefore
preserves this as distinct synthetic canonical identity `00U3 / Legacy
Management`, reachable only through the exact code/name alias; bare `0020`
remains intentionally ambiguous and unbound.

The accepted FY2022 P02, FY2023 P02, and FY2024 P09 snapshots exposed three
more transient Fossil Energy rows: `0301 / PROGRAM DIRECTION & SUPPORT` at
`-$2,120.80`, `0030 / PROGRAM DIRECTION` at `-$20.00`, and `0001 / OTHER
DEFENSE ACTIVITIES (DIRECT)` at zero cents. None appears in the account's
official final-year totals or all-history Program Activity inventory. The
FY2022 and FY2023 snapshots simultaneously contain material `0012 / PROGRAM
DIRECTION - MANAGEMENT`, so neither interim row is merged into the reviewed
Program Direction identity. Current PARK reference rows with the first and
third names belong to other DOE accounts, not `089-0213`. The registry
therefore preserves these three accepted source rows as exact-pair-only
synthetic identities `00U4`, `00U5`, and `00U6`, with no inferred PARK.

FY2026 P02 exposed 11 blank-code, blank-name rows with authoritative PARK
`61UPW3ZTCVT`, totaling exactly `$1,427,755.93`. The current official PARK
reference maps that key for account `089-0213` to compound PAC `0019`,
`Infrastructure Investment and Jobs Act/Bipartisan Infrastructure Law`.
The registry binds the PARK to that reviewed identity; it does not infer a
name from the blank File B presentation.

Before the serialized matrix reached the remaining FY2026 tail, the current
official PARK reference was cross-checked account-by-account against the
reviewed registry. For `089-0309`, every one of the 16 account-specific PARKs
(excluding the generic `PRE2018` sentinel) now resolves: exact legacy
successors retain their canonical pages, while National Technical Nuclear
Forensics, GTRI International Contribution, and reimbursable Global Material
Security remain distinct. For `089-2297`, seven additional reviewed PARKs are
covered; the IIJA and IRA demonstration identities and IRA Program Direction
remain distinct from the base program and base Program Direction. Tests parse
blank-name rows for every key so a future unknown PARK still fails closed.

## Accepted release evidence

PR [#32](https://github.com/jpwolfson/science-funding-dashboard/pull/32)
merged the atomic snapshot `efbabbfd02de824c9df88df5f793e741e8515eaf`
after durable run
[`31623029374`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/31623029374)
completed at attempt 11. Its terminal topology is 103 logical jobs: plan, all
100 account-year pulls, and reconcile succeeded; the branch-only deploy job
was skipped as designed. The restored branch head is
`e179057d525aced7a685f0992b7cd04dcc2b76b1`.

All values below are integer cents. Every accepted account-year reconciles
canonical File B exactly to the corresponding File A pin, and every
PA/reporting-period grain reconciles File C plus its explicit residual to File
B. The 93 individual year pins remain enumerated in the ten
`reference/doe_*_obligation_baseline.json` files.

| Account | Years | File A = File B | File C | File B - File C |
|---|---:|---:|---:|---:|
| ARPA-E | 10 | 355,986,876,363 | 311,654,562,486 | 44,332,313,877 |
| EERE | 10 | 5,032,606,483,227 | 4,614,106,372,951 | 418,500,110,276 |
| OCED | 5 | 1,291,234,868,529 | 831,618,852,661 | 459,616,015,868 |
| Fossil Energy | 10 | 895,943,264,878 | 758,152,837,999 | 137,790,426,879 |
| Electricity | 10 | 1,261,126,025,414 | 1,218,267,119,027 | 42,858,906,387 |
| CESER | 8 | 158,134,115,379 | 130,592,358,271 | 27,541,757,108 |
| Nuclear Energy | 10 | 1,920,679,558,123 | 1,773,209,476,345 | 147,470,081,778 |
| NNSA Weapons Activities | 10 | 18,370,987,559,777 | 16,155,217,062,964 | 2,215,770,496,813 |
| NNSA Defense Nuclear Nonproliferation | 10 | 2,282,736,909,861 | 2,098,929,887,476 | 183,807,022,385 |
| EIA | 10 | 126,085,907,726 | 53,142,544,617 | 72,943,363,109 |
| **Total** | **93** | **31,695,521,569,277** | **27,944,891,074,797** | **3,750,630,494,480** |

The accepted provenance contains 1,054 source-download snapshots with 414,905
parsed member rows, normalized to 75,919 signed events. Fail-closed Program
Activity resolution leaves zero unmapped identities, and obligation validation
completed with zero warnings. Overall File C/net is
`88.16668630524904%`; the residual is retained as ledger activity rather than
treated as missing data.

The reconciled DOE subtree is 52,087,296 bytes. Its compressed event
partitions are 8,846,282 bytes and provenance records are 1,822,044 bytes.
Attempt 11 elapsed 36h22m35s under the serialized matrix; reconciliation ran
8m12s. Workflow and restored-head verification both passed fast 7/7 and
rendered 3/3, with the rendered tier covering all 60 Wave 1 account/PA/theme
cases. Fresh deployed reader review also found the DOE landing, EERE account,
and Solar Energy PA pages legible and internally consistent in light and dark.

## FY2026 freshness prerequisite for DOT

DOT run `32520795528` reconciled all 30 requested partitions but correctly
failed because the already-live DOE SC FY2026 provenance had aged to 11 days
against the immutable 10-day SLA. Narrow recovery run `32554236811` refreshed
only DOE SC FY2026 P09. Its four-row semantic diff is recipient punctuation
only: row count, event IDs, amounts, period pin, and every dashboard numeric
series remain exact, with zero net amount change. The recovery retained ten
FY2017–FY2026 partitions, the `703809162794`-cent FY2026 P09 pin, zero warnings,
and 42-account sentinel coverage. Fast 7/7, rendered 4/4, 55 screenshots, and
the 258,024,920-byte assembled Pages footprint passed before PR #55; visual
review confirmed the FY2026 line still ends at P09.
