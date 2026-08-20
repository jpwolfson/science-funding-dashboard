# Phase 3.2d other-civilian sequencing-safe handoff

Prepared 2026-08-12 on `agent/3-2d-other-civilian-v2`, based on
authoritative main `689aba6a27f7f7282c444eacd583c4e694789bd7`.

## Non-negotiable release order

The ASPR availability probe is a hard dependency, not one ordinary scaffold
among several. The only valid history is:

```text
base 689aba6
  -> P: ASPR FY2024 single-period probe registration
  -> R: accepted official probe result and exact snapshot pins
  -> D: one atomic reconciled ASPR FY2024-FY2026 data commit
  -> VA -> DHS -> DOT -> IES -> AHRQ -> BLS/OJP scaffold commits
```

P completed as five serialized probes. P02 through P05 were source-empty; P06
was the first material period. Evidence-backed R and atomic data commit D are
now complete and merged through PR
[#33](https://github.com/jpwolfson/science-funding-dashboard/pull/33).
VA and later commits remain a separate local patch queue; the coordinator may
cherry-pick them only onto D or a descendant of D.

This ordering is mechanically enforced in
`tests/test_obligations_other_civilian.py`. If any VA-or-later account is
registered, the suite requires all of the following before it can pass:

1. an evidence-backed R state with exact FY2024–FY2026 pins;
2. a three-partition ASPR manifest containing only FY2024, FY2025, and FY2026;
3. accepted event/provenance files for every partition with File B and File C
   scope for internal account ID 7008;
4. normalized/provenance cents equal to the baseline pins; and
5. a warning-free, complete ASPR dashboard through FY2026 P09.

The full offline validator then independently checks the atomic store and
exact File B/File C reconciliation. A premature later-account cherry-pick
therefore fails the dedicated suite before a trigger can be justified.

## P — completed probe history

P appends only `hhs/aspr-rd-procurement` (`075-1000`, internal account ID
7008). The five pre-existing DOE/NSF entries are preserved byte-for-byte.
P initially exposed only:

```json
"2024": {"status": "partial", "asOfPeriod": 2, "firstPeriod": 2}
```

There was deliberately no `obligationsCents`, and FY2025/FY2026 remained
unavailable until the source boundary was proven. The coordinator ran P02,
P03, P04, P05, and P06 one at a time. P02–P05 returned header-only File B and
File C archives. P06 returned 20 File B rows and 59 File C rows and normalized
to 57 events totaling 44,099,377,125 cents through P06.

```json
{
  "mode": "custom",
  "accounts": "hhs/aspr-rd-procurement",
  "from_fy": 2024,
  "to_fy": 2024,
  "current_period": 6
}
```

The exact workflow and artifact identifiers for all five probes are recorded in
`reference/hhs_aspr_rd_procurement_probe_evidence.json`. P06 proves that the
registry and FY2024 baseline must begin at period 6; no earlier activity is
synthesized.

ASPR is the whole Research, Development, and Procurement account. It is not
BARDA-only coverage and does not resolve the provisional Project BioShield
crosswalk row.

## R — accepted official result

R satisfies the acceptance contract:

- account resolution exactly `075-1000` / ID `7008`;
- both `object_class_program_activity` and `award_financial` downloads finish;
- echoed account/FY/period scope exactly matches the request;
- ZIP, row-count, and archive-hash checks pass;
- normalization and probe-period reconciliation are exact; and
- no nonblank Program Activity identity is unmapped.

The discovered P06 boundary is recorded in both registry
`firstFiscalYearPeriod` and FY2024 `firstPeriod`. The baseline pins are
256,707,553,603 cents for FY2024, 301,354,965,654 cents for FY2025, and
192,325,603,497 cents for FY2026 P09. FY2024 remains partial, FY2025 is
complete, and FY2026 is partial through P09.

R adds `reference/hhs_aspr_rd_procurement_probe_evidence.json`; its tested core
shape is:

```json
{
  "schemaVersion": 1,
  "federalAccount": "075-1000",
  "accountId": "7008",
  "fiscalYear": 2024,
  "firstAcceptedPeriod": 6,
  "acceptedAt": "2026-08-14T07:32:11+00:00",
  "downloads": [
    {
      "submissionType": "object_class_program_activity",
      "status": "finished",
      "archiveSha256": "403553e072f6fddcf517ec0c38a8a0f2a42c9fbad3228d8148fc5067d96733b9",
      "statusRowCount": 20,
      "acceptedRequestScope": {
        "filters": {"federal_account": "7008", "fy": 2024, "period": 6}
      }
    },
    {
      "submissionType": "award_financial",
      "status": "finished",
      "archiveSha256": "6f73056c0a41d2caadd2358a2ec1b219a298196a9942e92a7856e693c166d42d",
      "statusRowCount": 59,
      "acceptedRequestScope": {
        "filters": {"federal_account": "7008", "fy": 2024, "period": 6}
      }
    }
  ],
  "accountSnapshots": [
    {
      "fiscalYear": 2024,
      "retrievedAt": "2026-08-14T07:34:30Z",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2024",
      "obligationsCents": 256707553603
    },
    {
      "fiscalYear": 2025,
      "retrievedAt": "2026-08-14T07:34:30Z",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2025",
      "obligationsCents": 301354965654
    },
    {
      "fiscalYear": 2026,
      "retrievedAt": "2026-08-14T07:34:30Z",
      "url": "https://api.usaspending.gov/api/v2/federal_accounts/075-1000/?fiscal_year=2026",
      "obligationsCents": 192325603497
    }
  ]
}
```

The tests compare all three snapshot cents to the baseline, validate the P06
request scopes, and reject a pending source citation. R makes the ASPR custom
FY2024–FY2026 planner emit exactly three jobs: FY2024 P12, FY2025 P12, and
FY2026 P09. R does not add the full data store.

## D — accepted atomic three-year ASPR reconciliation

After R passed, the coordinator ran the exact ASPR selector:

```json
{
  "mode": "custom",
  "accounts": "hhs/aspr-rd-procurement",
  "from_fy": 2024,
  "to_fy": 2026,
  "current_period": 9
}
```

All three years landed in reviewed atomic commit
`f5d43c3eb35d30f8c5758f587b56dc16d5a164b2`. D contains the ASPR event
partitions, accepted provenance, manifest, dashboards, registry-derived
aggregate updates, and combined sentinel. Trigger-restored head
`921ebf369a53c3dbc4857586f75320f1e347d2a1` merged at
`7b98acf7630ca301a8845698dbffe1d893251c56`.

Durable run
[`31780933170`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/31780933170)
has six terminal jobs: plan, all three pulls, and reconcile succeeded; the
branch-only deploy job was skipped. Across FY2024--FY2026, File A and canonical
File B each total `750,388,122,754` cents. File C totals `586,648,937,331`
cents and the explicit residual totals `163,739,185,423` cents, so File C plus
residual equals File B exactly. File C/net is `78.17940070505638%`.

The accepted store contains 743 signed events normalized from 5,451 parsed
rows in 29 source snapshots, with zero unmapped Program Activities or
validator warnings. The ASPR subtree is 352,843 bytes; compressed partitions
are 94,211 bytes and provenance records are 51,117 bytes. The run elapsed
47m24s and reconciliation ran 7m49s. ASPR registry passed 10/10, dedicated
tests 13/13, fast 7/7, and rendered 3/3 including 64 all-account light/dark
cases. The 22-page screenshot pack and live ASPR account/activity pages passed
reader review.

No VA or later scaffold was cherry-picked between R and D, and D was not split
into a one- or two-year state.

## Post-D patch queue and exact selectors

After D is committed, apply these reviewed append-only batches in order. Each
selector remains independent; do not combine ASPR with AHRQ.

| Batch | Exact selector | Range | Mechanical jobs |
|---|---|---|---:|
| VA | `va/medical-prosthetic-research` | FY2017–FY2026 P09 | 10 |
| DHS | `dhs/science-technology-rd,dhs/cisa-rd,dhs/cwmd-rd` | FY2017–FY2026 P09 | 30 |
| DOT | `dot/ost-research-technology,dot/faa-research-engineering-development,dot/fra-rd` | FY2017–FY2026 P09 | 30 |
| Education | `ed/ies` | FY2017–FY2026 P09 | 10 |
| AHRQ | `hhs/ahrq` | FY2017–FY2026 P09 | 10 |
| Statistics | `dol/bls,doj/ojp-research-evaluation-statistics` | FY2017–FY2026 P09 | 20 |

The reviewed account objects, exact pins, collision-safe aliases, and
presentation constraints in the prepared queue are unchanged from the source
brief. In particular:

- VA legacy Clinical Science identities remain separate from current CSP.
- CISA/CWMD historical organizations and CAS/non-CAS labels remain visible.
- OST-R is the parent; BTS/ARPA-I are subsets. Reused PACs stay distinct.
- FAA PAC 0012 variants and FRA rolling-stock variants remain distinct.
- IES is the parent and NCES a subset; IES Program Admin stays separate.
- AHRQ legacy reimbursable identities remain visible.
- BLS remains a statistical-capacity account.
- OJP is the parent; BJS and NIJ are Program Activities.

## Evidence sources

- Account snapshots:
  `https://api.usaspending.gov/api/v2/federal_accounts/{CODE}/?fiscal_year={FY}`
- PA/PARK inventory:
  `https://api.usaspending.gov/api/v2/federal_accounts/{CODE}/program_activities/?limit=100&page=1&order=asc&sort=code`
- Program Activity contract:
  <https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/federal_accounts/federal_account_totals/program_activities.md>
- Custom account contract:
  <https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/accounts.md>
- Crosswalk: `reference/aaas_federal_account_crosswalk.json`

## P verification

Before publishing or running the probe, P must have:

- ASPR registry: 10/10;
- whole registry: 45/45;
- dedicated tests: green with the exact one-job and multi-year-block assertions;
- full planner: 51 registry jobs, only one attributable to ASPR;
- fast tier: 7/7;
- clean diff and ownership limited to the registry append, ASPR staging
  baseline, this handoff, and the dedicated test module.

No remote operation, trigger, download, CI run, result evidence, pin, or data
store is claimed by P.

## VA release — scaffold on current main

The reviewed VA queue entry was replayed onto live main
`7be7fcc782cbb3d56dbaf86745807b01e37a873b` without changing the first 38
registry accounts. It appends only `va/medical-prosthetic-research`
(`036-0161`) and its exact FY2017–FY2026 File A baseline. The registry object
and baseline match prepared queue commit `e0985f0316bb4e86ad4deae0f39a6786d9e3bb74`;
legacy Clinical Science identities remain distinct from current CSP.

Pre-source gates passed: VA registry 10/10, whole registry 276/276 with 39
unique account paths/codes, other-civilian 13/13 (four later-stage skips),
and fast 7/7. The source selector is exactly
`va/medical-prosthetic-research`, full FY2017–FY2026 (ten jobs). No source
run, atomic data store, or release completion is claimed by this scaffold.
Because reconciliation changes dashboard series geometry, the merged release
must include rendered verification and a before/after screenshot comparison
of the affected VA and aggregate charts.
