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

CISA FY2019 attempt 1 stopped at P03 on the historical exact key
`0003 / CAS - CYBERSECURITY`. The retained raw artifact is `9435858556`
(1,048 bytes; SHA256
`1713eadc6c269bf6700cbc31f7cbd609dd82bae37ebfbd86f947c23acf8e3972`).
Its P03 archive is 422 bytes with SHA256
`9389d521126379687e0f01b6a1689a16235fd97074eb590927cba17c72331336`;
the eight preserved rows include five exact-key rows totaling 101,511 cents.
The identical activity name and the later canonical `0001` key make this an
unambiguous historical alias. The repair changes no source total, File A pin,
tolerance, or residual, and the trigger remains unchanged.

CISA FY2020 attempt 1 later stopped after the complete File B P02--P12 pull
and File C P12 pull on `OPTN / FIELD IS OPTIONAL PRIOR TO FY21`. The retained
raw artifact is `9436198050` (8,078 bytes; SHA256
`7276d507eac06ec9a01c456ac869e3cf53f01ad8878573b871f8021789d73c3c`).
Its 2,103-byte File C archive has SHA256
`4d08862a56d3f369bd7d103096b898d384b304ee05c8387a8023578657a95b3c`;
the six contract rows total 364,438,567 cents. Because the source explicitly
states that the activity field is unavailable before FY2021, this exact key
maps to the existing `Unknown / other` identity. The mapping preserves every
source cent and changes no File A pin, tolerance, or residual.

CISA FY2026 attempt 1 stopped at P02 on blank code/name PARK
`5ZD2V505R8T`. Retained raw artifact `9438252034` is 547 bytes with SHA256
`623bcda56b8f15e4329ef0ac9fdcfdcbc2d03248633d6ee2c18d8ca0f7f8d414`;
its sole 392-byte inner archive has SHA256
`61bfe10405ec6601c227a1b0ffe8a6f2984ceeec1267c115e484f4de593dbce3`
and preserves exactly nine File B rows, including two zero-cent rows for the
new PARK. Treasury's official DATA Broker mapping file at commit
`dfc87000f6fc88fe1da0beead77e6640897132e0` (file SHA256
`e0e72fea7838a70d261bf9641e41b84d899d446eecdbc138f9965a1f33753210`)
maps that exact PARK and federal account `070-0805` to
`CAS - Cybersecurity`. The repair therefore adds the PARK to the existing
CISA cybersecurity identity. It changes zero cents and no File A pin,
tolerance, or residual.

CWMD FY2020 attempt 1 completed the full File B P02--P12 pull and File C P12
pull before stopping on the same exact pre-FY21 placeholder,
`OPTN / FIELD IS OPTIONAL PRIOR TO FY21`. Retained raw artifact `9439855008`
is 16,706 bytes with SHA256
`95a1b20395d348c716087860f3deeed40f801afdebe837c2158c302fbc374211`.
Its 7,439-byte File C archive has SHA256
`9f3983db6fef1e76707f37f1e8c91aced2dfb95098883409aea58f3be10cb0d2`
and contains exactly 102 rows: five assistance rows totaling
`-75,366,602` cents, 92 contract rows totaling `4,751,474,648` cents, and
five unlinked rows totaling `380,636,791` cents. All 102 rows share the one
exact placeholder key and total `5,056,744,837` cents. The account-scoped
repair maps that key to CWMD's existing `Unknown / other` identity, preserving
every source cent and changing no File A pin, tolerance, or residual. It is
an exact mapping repair, not a File A/File B variance.

Science and Technology FY2020 attempt 1 completed the full File B P02--P12
pull and File C P12 pull before stopping on the same exact pre-FY21
placeholder, `OPTN / FIELD IS OPTIONAL PRIOR TO FY21`. Retained raw artifact
`9444494944` is 35,756 bytes with SHA256
`f0ea3548fb7e8058263dbdf873848b6882a2632bf93295311a8bef178eb6fca3`.
Its 27,395-byte File C archive has SHA256
`808b5289a43737cc9375fac33d0d3cd13b37410525b25d739ecffc2855397664`
and contains exactly 355 rows: 21 assistance rows totaling `3,122,108,056`
cents, 332 contract rows totaling `25,512,701,071` cents, and two unlinked
rows totaling `265,285,720` cents. All 355 rows share the one exact
placeholder key and total `28,900,094,847` cents. The account-scoped repair
maps that key to Science and Technology's existing `Unknown / other`
identity, preserving every source cent and changing no File A pin,
tolerance, or residual. It is an exact mapping repair, not a File A/File B
variance.

Attempt 1 source run `32449818249` is terminal after the complete selector.
Its `filter=all`, `per_page=100` inventory is exactly 33 raw jobs on page 1
with page 2 empty: plan and 25 pulls succeeded, the five reviewed pulls above
failed, and reconcile plus deploy skipped. All remaining Science and
Technology pulls, including FY2026, succeeded; no additional failure or
mapping gap appeared. The complete artifact inventory is 55 on page 1 with
page 2 empty. The five repairs therefore constitute the complete semantic
repair for this attempt.

Attempt 2 of source run `32449818249` reran only those five failed pulls. Its
complete `filter=all`, `per_page=100` inventory is 66 raw executions on page 1
with page 2 empty: all 30 latest logical pulls succeeded, reconcile failed,
and deploy skipped. Reconcile assembled and validated the full candidate but
the fast tier correctly rejected the stale CWMD FY2026 single-pin assertion.
No candidate commit or normalized recovery artifact was used. The complete
artifact inventory is 65 on page 1 with page 2 empty.

The official FY2026 P09 GTAS/File A endpoint for CWMD returned
`2,380,850,844` cents (response SHA256
`934909ac98b58d81f9bcd3718d9e5343ba63ba5c7311eb5bd691d2d8cff321b8`).
Source job `96781297151` retained raw artifact `9442894725` (outer SHA256
`5d7786c826ff264cb07aa24cf6c493b47ab87d24836da4c2d2df66a12f64ef4c`);
its 36-row P09 File B archive has SHA256
`f7d5b0868c9b10bc846ffc28e9d7bf04255a1c39f5136a40d22590f0cad60458`
and totals `2,502,737,329` cents. File A minus File B is exactly
`-121,886,485` cents (`-$1,218,864.85`, 5.1195% of File A). The owner approved
publishing File B as canonical on 2026-08-21 while preserving the exact File A
total. No tolerance or synthetic residual is introduced. The machine-readable
and human-readable source-variance ledgers record the same evidence and remain
release-pending until merge, deploy, and live QA.

The approved dual pin exposed two fail-closed reconcile defects without
changing source data. Attempt 3 failed because the reconciler still replaced a
newer approved dual pin with stale retained-artifact metadata. Shared fix PR
[#52](https://github.com/jpwolfson/science-funding-dashboard/pull/52) merged at
`0aac02cf7b7b0affce535ab1cbd7d6efe7f5e8b4`; it preserves a dual pin only when
the current row is schema-valid and its File B total, status, `asOfPeriod`, and
`firstPeriod` exactly match the accepted artifact. The DHS branch integrated
that fix at `ef570f72276593e7629d798aa799c79037807827` without changing any DHS
source subtree. Only the failed attempt-3 reconcile job was rerun; no pull job
or normalized recovery artifact was replayed.

Attempt 4 is terminal green. The complete `filter=all`, `per_page=100`
inventory for run `32449818249` is exactly 132 raw executions: page 1 has 100,
page 2 has 32, and page 3 is empty. Its latest logical topology is exactly 33
jobs: plan, all 30 carried successful FY2017--FY2026 pulls, and reconcile
succeeded; deploy skipped. Atomic commit
`3811989e84bf4b7209fe2e055e916419515cf50f` is a strict child of the integration
commit. Each DHS account has an exact 21-file, ten-partition event store;
Science and Technology, CISA, and CWMD respectively resolve to
`439260355410`, `7315581281`, and `77040747914` total net obligation cents,
with zero warnings. DHS totals `523616684605` cents, the root totals
`86716604619486` cents, and the sentinel covers exactly 42 financial accounts.
The approved CWMD FY2026 row remains File A `2380850844` cents, canonical File B
`2502737329` cents, and exact variance `-121886485` cents with no tolerance or
synthetic residual. Trigger restore
`a23daa6370568597a381148d698a7f99c2dc7038` is a strict child of the atomic
commit and changes only `.github/triggers/update-obligations.json` to main's
exact weekly/all blob `8c9688525108cc68160c78494993bb0a91376a19`.

Pre-merge release gates on the restored, zero-behind branch passed:
other-civilian plus obligation validation 28/28 with three expected later-stage
skips; registry 297/297 with 42 unique paths and codes; fast 7/7; rendered 4/4
(5 core, 168 all-account, 59 assembled-artifact public-link, and 2 sentinel
cases); and screenshots 55/55. The mandatory chart-geometry review compared
the 51-page pre-DHS main pack with the 55-page DHS pack. The root FY2026
cumulative line and each of the three new DHS account lines stop at P09 (June)
rather than extending flat through July--September; the DHS representative
activity and sentinel pages show no visible diagnostics. Footprint is
`558588770` tracked bytes, `556843654` data bytes, and `334359696`
compressed-store bytes. The assembled Pages artifact is `258024917` bytes
across 1,583 files, status `ok`, with `741975083` bytes of headroom below the
1 GB limit; obligation event archives remain excluded from Pages and linked
only through GitHub.

Release PR [#53](https://github.com/jpwolfson/science-funding-dashboard/pull/53)
tracks the terminal pre-merge CI evidence for this exact tree.

PR #53 merged at `37bca577ed75d1f9107853179667e21bd7b0114b`. Post-merge
Test run `32516046467` and Deploy Pages run `32516046481` are each terminal
with exactly one successful job on page 1 and page 2 empty. Live root,
obligation index, DHS rollup, all three account dashboards and manifests, and
sentinel JSON are byte-exact with the merged tree. Live light and dark renders
of the three accounts, a representative CISA activity, and the sentinel had
zero diagnostics; the FY2026 account lines visibly stop at P09 (June). DHS and
the approved CWMD FY2026 File A/File B variance are therefore live.

## DOT release — scaffold on live DHS main

The DOT batch is based exactly on live DHS main
`7d39b03abdb7ca74c3fffc87e01924ee50621c56` and preserves all 42 live
accounts. It appends only `dot/ost-research-technology` (`069-1730`),
`dot/faa-research-engineering-development` (`069-8108`), and `dot/fra-rd`
(`069-0745`) with the reviewed FY2017--FY2026 File A baselines. The exact
source selector is those three paths, full FY2017--FY2026, for 30 mechanical
pull jobs.

The reviewed collision contract remains intact: OST-R is the parent while
BTS and ARPA-I remain subsets; reused OST-R codes retain distinct names and
PARKs; FAA PAC `0012` variants remain distinct; and FRA rolling-stock
identities remain distinct. No Education or later civilian account is
registered by this scaffold. Source, atomic reconcile, 45-account sentinel,
weekly/all trigger restore, current-main integration, release gates including
affected-chart screenshot comparison, merge/deploy, and live QA remain
required before DOT can be called complete.

The first source attempt exposed one reviewed exact-key spelling alias in
OST-R FY2023 P02: PAC `0004`, blank PARK, `ADVANCES RESEARCH PROJECTS -
INFRASTRUCTURE`. It is the zero-cent spelling variant of the registered
`ADVANCED RESEARCH PROJECTS - INFRASTRUCTURE` identity. Retained raw artifact
`9469274657` is 1,105 bytes with SHA256
`dccd4492a414bb4efea61d8585e23de91385472413de9d295d1f7770a26e7910`;
its sole 890-byte source archive has SHA256
`8357716c8bc50d5e0facd95f26758562e396dcebe709dcb99139cb1a1f8b8305`
and contains 54 rows totaling 395,096,572 cents, with the exact alias row at
zero cents. This is a mapping repair only: no File A/File B variance, pin,
tolerance, residual, or published amount changes.

The original DOT run `32520795528` is terminal and retired. Its complete
`filter=all`, `per_page=100` inventory is 66 raw executions on page 1 with
page 2 empty; artifacts are 61 on page 1 with page 2 empty. The failed-job
retry resolved the spelling alias, but reconcile then stopped only because
the already-live DOE SC FY2026 snapshot had aged to 11 days against the
immutable 0--10-day freshness SLA. DOE SC was refreshed separately in live
PR #55. No DOT normalized artifact from the retired graph was reused.

Fresh source run `32561912975` attempt 1 is terminal green. Its complete
`filter=all`, `per_page=100` inventory is exactly 33 jobs on page 1 with page
2 empty: plan, all 30 fresh FY2017--FY2026 pulls, and reconcile succeeded;
deploy skipped. The complete artifact inventory is exactly 60 on page 1 with
page 2 empty, one fresh raw and one normalized artifact for each pull. Atomic
commit `572371808557f7a368ee4602423543ef49eb71af` is a strict child of source
commit `753fb7e72007ea8efdd2249c84548d38744ac8bf`. Each account has an exact
21-file, ten-partition store and exact baseline pins with zero warnings.
OST-R, FAA RE&D, and FRA R&D respectively resolve to `43,482,440,899`,
`196,566,776,602`, and `39,414,052,293` total net obligation cents; DOT totals
`279,463,269,794` cents, the root totals `86,996,067,889,280` cents, and the
sentinel covers exactly 45 unique financial accounts. Weekly/all restore
`848836568ef89ffd2bfb34f91b9ef27d57ace013` changes only the trigger to main's
exact blob `8c9688525108cc68160c78494993bb0a91376a19`. Then-current main remains
`71f7246839bc14af39c5f9678ffbb638cfdeec78`, already an ancestor through the
reviewed exact-union integration commit.

Pre-merge release gates passed: other-civilian plus obligation validation
28/28 with two expected later-stage skips; registry 45/45 unique paths and
federal accounts; fast 7/7; rendered 4/4 (5 core, 180 all-account, 59 public
link, and 2 sentinel cases); and screenshots 59/59. The mandatory geometry
review compared the 55-page main pack with the 59-page DOT pack. The root and
all three DOT FY2026 cumulative lines end at P09 (June), with no extension
through July--September; the DOT representative activity and sentinel pages
show no visible diagnostics. The assembled Pages artifact is 264,928,975
bytes across 1,655 files, status `ok`, with 735,071,025 bytes of headroom;
obligation archives remain excluded. The repo is 566,468,174 tracked bytes
with 335,316,536 compressed-store bytes. Relative to main, the deltas are
7,874,781 tracked bytes, 7,860,899 data bytes, 956,844 compressed-store bytes,
and 6,904,055 Pages bytes; the historical-backfill trajectory remains flagged
only as a conservative upper bound.

Release PR [#56](https://github.com/jpwolfson/science-funding-dashboard/pull/56)
tracks the terminal pre-merge CI evidence for this exact tree.

PR #56 merged at `cdafdf8ad5a5cc4c87d921f1faecc2093dae10d8`.
Post-merge Test run `32588659008` and Deploy Pages run `32588659026`
are each terminal with exactly one successful job on page 1 and page 2 empty;
the complete head-SHA run inventory is exactly those two runs on page 1 with
page 2 empty. Live root/index/DOT, all three account dashboards and manifests,
and sentinel JSON are byte-exact with the merged tree. A fresh 14-case live
light/dark render matrix covering the root, DOT, all three accounts, one OST-R
activity, and the sentinel completed with zero render, network, or browser
diagnostics. The root, DOT, account, and activity FY2026 lines visibly stop at
P09 (June). DOT is therefore merged, deployed, and live-QA complete.

## IES release — scaffold on live DOT main

The IES batch starts from exact live DOT main
`cdafdf8ad5a5cc4c87d921f1faecc2093dae10d8` and preserves its 45 live
accounts. It appends only `ed/ies` (`091-1100`) and the reviewed
FY2017--FY2026 File A baseline. The exact source selector is `ed/ies`, full
FY2017--FY2026 through P09, for ten mechanical pull jobs.

IES remains the parent account and NCES remains a subset. Historical PAC and
current PARK identities reconcile to the same canonical activities, while
IES Program Admin remains separate. No AHRQ, BLS, OJP, BEA, or DoD account is
registered by this scaffold. Atomic reconcile, 46-account sentinel,
weekly/all restore, then-current-main integration, fast/rendered/screens and
footprint gates, merge/deploy, byte-exact live JSON, and affected-chart
light/dark screenshot comparison remain required before IES is complete.
