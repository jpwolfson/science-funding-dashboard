# Phase 3.2d DOE handoff

## Scope and status

This branch onboards the ten crosswalk-resolved DOE accounts in roadmap
3.2d-1A and 3.2d-1B. DOE Office of Science (`089-0222`, `doe/sc`) remains the
untouched Phase 3.1b regression fixture. No account is parked and no shared
adapter, validator, workflow, site, sentinel, or trigger file changed.

The registry, official-title review, Program Activity inventory, source-
availability scaffolds, and DOE-specific tests are complete. Historical data,
exact-cent baseline pins, dashboards, rendered evidence, and runtime/footprint
figures are intentionally pending the CI full backfill; local USAspending
egress is unavailable.

## Official account evidence

Account titles and Program Activity inventories were read from USAspending's
official federal-account endpoints for FY2026. The inventory count is the raw
endpoint count across PAC/PAN and PARK rows; the normalized count is the unique
published identities after reviewed aliases and duplicate historical labels.

| Account | Path | Official account title | Bureau | Inventory | Normalized | Status |
|---|---|---|---|---:|---:|---|
| `089-0337` | `doe/arpa-e` | Advanced Research Projects Agency-Energy, Energy Programs, Energy | Energy Programs | 7 | 4 | ready for backfill |
| `089-0321` | `doe/eere` | Energy Efficiency and Renewable Energy, Energy Programs, Energy | Energy Programs | 32 | 26 | ready for backfill |
| `089-2297` | `doe/oced` | Clean Energy Demonstrations, Energy Programs, Energy | Energy Programs | 33 | 16 | ready for backfill |
| `089-0213` | `doe/fossil-energy` | Fossil Energy, Energy Programs, Energy | Energy Programs | 52 | 27 | ready for backfill |
| `089-0318` | `doe/electricity` | Electricity, Energy Programs, Energy | Energy Programs | 29 | 19 | ready for backfill |
| `089-2250` | `doe/ceser` | Cybersecurity, Energy Security, and Emergency Response, Energy Programs, Energy | Energy Programs | 14 | 11 | ready for backfill |
| `089-0319` | `doe/nuclear-energy` | Nuclear Energy, Energy Programs, Energy | Energy Programs | 58 | 29 | ready for backfill |
| `089-0240` | `doe/nnsa-weapons-activities` | Weapons Activities, National Nuclear Security Administration, Energy | National Nuclear Security Administration | 34 | 29 | ready for backfill |
| `089-0309` | `doe/nnsa-defense-nuclear-nonproliferation` | Defense Nuclear Nonproliferation, National Nuclear Security Administration, Energy | National Nuclear Security Administration | 18 | 16 | ready for backfill |
| `089-0216` | `doe/eia` | Energy Information Administration, Energy Programs, Energy | Energy Programs | 7 | 3 | ready for backfill |

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

To be filled from the accepted CI snapshot before opening the PR:

- exact File B/File A cents by account and FY;
- File C/net figures, zero-warning reconciliation, and unmapped PA result;
- accepted provenance coverage and raw/normalized counts;
- `verify.py --tier fast --json` and `--tier rendered --json` outputs;
- light/dark rendered QA;
- runtime, compressed artifact growth, and PR URL.
