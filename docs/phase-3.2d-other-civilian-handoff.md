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

## VA release — live-ready reconciled branch

The reviewed VA queue entry was replayed onto live main
`7be7fcc782cbb3d56dbaf86745807b01e37a873b` without changing the first 38
registry accounts. It appends only `va/medical-prosthetic-research`
(`036-0161`) and its exact FY2017–FY2026 File A baseline. The registry object
and baseline match prepared queue commit `e0985f0316bb4e86ad4deae0f39a6786d9e3bb74`;
legacy Clinical Science identities remain distinct from current CSP.

Pre-source gates passed: VA registry 10/10, whole registry 276/276 with 39
unique account paths/codes, other-civilian 13/13 (four later-stage skips),
and fast 7/7. The source selector is exactly
`va/medical-prosthetic-research`, full FY2017–FY2026 (ten jobs).

Durable source run
[`32412548096`](https://github.com/jpwolfson/science-funding-dashboard/actions/runs/32412548096)
is terminal green after two reconcile-only repairs. Its complete
`filter=all`, `per_page=100` inventory is 39 raw executions on page 1 with
page 2 empty. Attempt 1 pulled all ten years successfully but reconcile found
a stale scaffold assertion. Attempt 2 passed reconciliation but fast testing
detected that the first connector publication had encoded macOS `base64`
error text as the test blob. Corrective commit
`59f3839c6758fd7210478f0ff3a4bf1e961c329b` restored byte-exact UTF-8 test
and handoff blobs. Attempt 3 then completed the latest logical topology:
plan, all ten FY2017–FY2026 pulls, and reconcile succeeded; deploy skipped.
The complete artifact inventory is 20 on page 1 with page 2 empty: ten
normalized partitions and ten distinct attempt-specific raw archives. No
normalized recovery artifact was used. There was no File A/File B variance,
dual pin, tolerance, or residual change.

Atomic commit `23cb0ea4f423a0981062a7894bb8d6e78f7b3970` contains the exact
21-file, ten-partition event store, accepted provenance and manifest, rebuilt
VA/root rollups, no warnings, and 39-account sentinel coverage. VA resolves to
`036-0161`, FY2026P09, 15 child activities, and
`870,126,042,476` total net obligation cents. Its exact FY2017–FY2026 pins are
`72,059,060,435`, `73,441,493,028`, `82,205,074,686`, `84,897,709,754`,
`93,679,357,008`, `98,664,584,822`, `102,409,481,598`, `103,621,061,988`,
`96,999,597,865`, and `62,148,621,292` cents. Trigger restore
`d2e1605d236b8584eccf65bd85ad1c5bfa000560` exactly matches main's
weekly/all blob `8c9688525108cc68160c78494993bb0a91376a19`. Integration merge
`d4fdb2c0daecc2d0521b20404b13804bad9dcd4c` has the restored VA head as
primary parent and then-current main `7be7fcc782cbb3d56dbaf86745807b01e37a873b`
as its second parent; it is zero behind main and preserves an exact
39-account union.

Post-integration gates passed: other-civilian 13/13, VA registry 10/10,
whole registry 276/276, fast 7/7, rendered 4/4 (5 core, 156 all-account,
59 public-link, and 2 sentinel cases), and screenshots 51/51. The mandatory
before/after chart review compared the 49-page main pack with the 51-page VA
pack: the root and VA FY2026 cumulative lines stop at P09 (June) rather than
extending flat through the remaining fiscal-year axis; the VA account,
representative activity, and sentinel pages have no visible diagnostics.
The footprint is 553,589,102 tracked bytes, 551,876,034 data bytes,
333,780,227 compressed-store bytes, and a 253,636,766-byte Pages artifact
with 746,363,234 bytes of headroom. Relative to pre-VA main, the deltas are
1,553,139 tracked bytes, 1,547,142 data bytes, 39,022 compressed-store bytes,
and 1,508,120 Pages bytes. This fulfills the chart-geometry verification rule
for the VA reconciliation.

Source run `32412548096` completed the plan and all ten FY2017--FY2026 pulls.
Reconciliation and obligation validation passed, but its fast tier exposed a
scaffold assertion that treated every newly registered account as a forbidden
later store even after the active VA store had materialized. The assertion now
rejects stores only for accounts absent from the cumulative registry stage;
no source data, pin, tolerance, residual, or published amount changed.

The first remote publication of that correction encoded both edited text
files as binary, so attempt 2 again reconciled and validated successfully but
failed while importing this test module. The corrective descendant restores
the reviewed UTF-8 blobs exactly; it makes no additional semantic or data
change.

## DHS release — scaffold on live VA main

The DHS batch is based exactly on live VA main
`5e83e0c348e75e6d131121baf4a8b0882a79775f` and preserves all 39 live
accounts. It appends only `dhs/science-technology-rd` (`070-0803`),
`dhs/cisa-rd` (`070-0805`), and `dhs/cwmd-rd` (`070-0860`) plus their reviewed
FY2017–FY2026 File A baselines. The exact source selector is those three paths,
full FY2017–FY2026, for 30 mechanical pull jobs.

The reviewed collision contract remains intact: historical and current CISA
CAS labels are distinct; CWMD CAS and non-CAS identities sharing codes remain
distinct; PARK-backed current identities remain canonical. No DOT or later
civilian account is registered by this scaffold. Source, atomic reconcile,
42-account sentinel, trigger restore, release gates, merge/deploy, and live QA
remain required before DHS can be called complete.
