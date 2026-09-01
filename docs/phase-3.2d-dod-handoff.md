# Phase 3.2d DoD obligation handoff

## Release status

Owner approved quarantining the nonterminal OJP and BEA source jobs on
2026-08-27 and proceeding with DoD on an isolated release branch. The exact
OJP and BEA handles, branches, raw artifacts, and recovery manifests remain
untouched. This DoD branch starts from authenticated current main
`b7753ab1c598c7cad8c7e7251ddffe3067c510fe`; the stale, dirty stage-A worktree
was used only as historical evidence and was not reused as an execution tree.

DoD runs as three source graphs, exactly one graph at a time:

1. Army RDT&E (`021-2040`) and Navy RDT&E (`017-1319`);
2. Air Force RDT&E (`057-3600`) and Space Force RDT&E (`057-3620`); and
3. Defense-Wide RDT&E (`097-0400`) and Defense Health Program (`097-0130`).

Reader review and owner sign-off on the public disclosure remain mandatory
before merge. Source, reconciliation, rendered, screenshot, footprint,
deployment, live-QA, and weekly-soak evidence will be appended as each gate
becomes terminal.

## Public interpretation contract

File B account obligations are canonical. File C supplies recipient, award,
instrument, and transaction detail only for the award-linked subset. DoD can
have sparse public File C attribution because classified, intramural,
interagency, and contract-heavy activity may not appear with equivalent public
award detail. A low File C/net ratio is therefore an attribution limitation,
not evidence of missing account dollars. The signed residual remains explicit,
and `File C + residual = File B` must reconcile exactly at every accepted
account/Program Activity/period grain.

The five RDT&E account totals support an explicit service/Defense-Wide account
aggregate. They do not reconstruct AAAS 6.1, 6.2, 6.3, or 6.1–6.6
budget-activity views. No Program Activity name, File C instrument class, or
account arithmetic is presented as those alternate concepts.

## Stage 1 scaffold — Army and Navy

The first scaffold appends only `dod/army-rdte` and `dod/navy-rdte`, their
reviewed File A/GTAS FY2017–FY2026 pins, collision-safe PARK and exact
code/name aliases, this handoff, and dedicated tests. It does not include a
source store or claim source completion.

The official USAspending federal-account endpoint was rechecked on 2026-08-27
for every FY2017–FY2026 pin. Army pins are `1335551508911`, `1658237560606`,
`1941282900467`, `2944022806618`, `5649553107182`, `5252715920406`,
`2826746057722`, `2462016948008`, `2432841622809`, and `1899886149032`
cents. Navy pins are `1815670608261`, `1906604818960`, `1989612897412`,
`2110379803523`, `2104077406079`, `2211161457342`, `2645738486155`,
`2956285398710`, `2788535575911`, and `2552546450852` cents. FY2017 is
partial from P06, FY2018–FY2025 are complete, and FY2026 is partial through
P09.

The exact stage-1 source selector is
`dod/army-rdte,dod/navy-rdte`, FY2017–FY2026 through P09, yielding twenty
mechanical pull jobs. The trigger remains weekly/all until the scaffold commit
is pushed; source activation is a separate strict-child trigger commit.

Stage-1 attempt 1 is workflow run `33145859877` at exact trigger commit
`87d0e956b48c0483c3fd48cd4dd9fc6272e04df7`. Army FY2018 job
`98766675128` stopped on the exact source key code `0007`, blank PARK,
name `OPERATIONAL SYSTEMS DEVELOPMENT`. The preserved raw artifact
`9675960262` has SHA-256
`f52370aaf185974276a9d7486c085157350519a1ef939a58a393fbaef7edd201`.
That plural label is an exact alias of the existing Army code-`0007`
Operational System Development identity, matching the already-reviewed Navy
alias. Parsing the preserved P03 File B rows after adding the alias retains the
byte-derived scoped total exactly: `281828620500` cents before and after
mapping. This is an identity-only, zero-dollar-impact recovery; the active
graph remains untouched until terminal.

The same attempt subsequently exposed three more exact source labels, also
without changing any amount or canonical meaning:

- Army FY2020 job `98766675192`: File C placeholder code `OPTN`, name
  `FIELD IS OPTIONAL PRIOR TO FY21`, mapped to the explicit Unknown / other
  identity. Raw artifact `9676754335` has SHA-256
  `7c9812010a055611ca5671d79b98d7b4a25d32674fe79eaf653222e1f9d95776`.
  The preserved File C rows total `1015650607391` cents both before and
  after mapping; the File B P12 total remains its exact
  `2944022806618`-cent pin.
- Army FY2021 job `98766675179`: code `0005`, name
  `SYSTEM DEVELOPMENT & DEMONSTRATION ($DD)`, mapped to the existing System
  Development and Demonstration identity. Raw artifact `9677014688` has
  SHA-256
  `ccf2658ebc27f6acbd33c5bcc0aaba463da54360434cd3e59897a7cb48fc959e`.
  All preserved P02–P11 File B snapshots parse byte-for-byte; P11 remains
  `4947492231746` cents before and after mapping.
- Army FY2023 job `98766675213`: code `0050`, name `N/A`, mapped to the
  explicit Unknown / other identity. Raw artifact `9677392564` has SHA-256
  `1fcff8ba0e066e2b81d6efa402fef68d7a8c18b168c2660bd69258c9a11a9e06`.
  The preserved P02 File B snapshot remains `239465750151` cents before and
  after mapping.
- Navy FY2020 job `98766675824`: File C placeholder code `OPTN`, name
  `FIELD IS OPTIONAL PRIOR TO FY21`, mapped to Navy's explicit Unknown /
  other identity. Raw artifact `9680105630` has SHA-256
  `9353e8709afc0bde9b2ba37c4d1d9e7456ad2a06cd9e867db8c6c9ffd8cf3663`.
  Every preserved File B and File C archive parses exactly after the alias;
  File C remains `433074725418` cents and File B P12 remains its exact
  `2110379803523`-cent pin before and after mapping.
- Navy FY2026 job `98766676044`: blank code/name with exact PARK `PRE2018`,
  mapped to the standard explicit `ACTIVITY FROM OBLIGATION BEFORE FY 2018:
  PROGRAM ACTIVITY NOT SPECIFIED` identity. Raw artifact `9682368544` has
  SHA-256
  `2d40c4c4e989526692c240d688aa938154db9978e03c120b34d40b940783aa93`.
  Its triggering P03 `PRE2018` row is exactly zero cents; every preserved
  File B row parses after the exact PARK mapping and P03 remains
  `529352333650` cents before and after.

Navy FY2025 job `98766675969` is a separate owner gate, not an identity
repair. Raw artifact `9682337050` has SHA-256
`91c2d7b8ae7ac6e5ab757fbccb35460eb7a09eea370a6d1b041826b6415633d8`;
its nested official P12 File B ZIP has SHA-256
`ffd3b2ef0e0047487f50ccb5beef52cd0142fe82666908dcd17ad3e16af1cca7`
and totals `2788488646275` cents. The independent official, date-filtered
Program Activity endpoint returns the same exact total across all 15 rows,
while the official GTAS/File A account snapshot and existing pin remain
`2788535575911` cents. File A minus File B is therefore exactly `46929636`
cents ($469,296.36). The preserved File A response has SHA-256
`58801fb959910856950313eeba6f123d72540663748d340d29dcdd3bd3edac16`;
the separately preserved 15-row Program Activity response has SHA-256
`868572fa3d0ec67b006344c4cd75c649676ad5c75430c598399e1b7963f1e030`
and declares no next page. The owner approved preserving both exact totals on
2026-08-28. The FY2025 baseline now uses the universal exact dual-pin schema,
and the source-variance ledger records the `46929636`-cent variance as pending
release. File B remains canonical; no tolerance or synthetic residual is used.

These mappings are exact-key additions only. They neither relax the fail-closed
parser nor modify a File A pin, File B total, tolerance, or public semantic.

Stage-1 targeted recovery attempt 5 reran only Army FY2023 after the initial
code-`0050`, name-`N/A` identity repair. The attempt stopped at the later P09
snapshot on two additional exact source labels: code `0002`, name `N/A`, at
`25000000` cents and code `0006`, name `N/A`, at `15000000` cents, both with
blank PARK. The retained raw artifact `9711320717` has SHA-256
`68ecc4074da33b094eda48328dc32d8ac62c63141534ae89df4974c74cac9407`.
An exhaustive parse of every retained P02–P09 File B row found no other
unmapped identity. Both labels follow the account's existing exact `N/A`
precedent and map to explicit Unknown / other; they do not fall through by
bare code to canonical Applied Research or Management Support. The exact P09
File B total remains `1977061254246` cents before and after attribution. This
is an exact-key attribution repair only: it changes no source dollar, pin,
tolerance, or public semantic.

Targeted recovery attempt 7 reran only Navy FY2020. The actual execution,
job `99094394596`, completed successfully with every executed step green.
GitHub also emitted two duplicate same-partition records, `99094394577` and
`99094394614`, which remained queued with null conclusions and no executed
steps even though run `33145859877` itself was terminal. Repeated authenticated
REST checks found those two records byte-for-byte unchanged for more than
thirteen hours. The owner approved treating them as inert copied placeholders
on 2026-08-30. This exception changes neither the successful source result nor
the one-partition-at-a-time recovery rule; the two placeholder IDs must never
be rerun or counted as executions.

## Stage 1 terminal result

Owner-approved recovery commits `087609a885ca74145ad52b224f99406da4b74804`,
`a793ee3ad85f46154054e0449d19d083dbcf3bce`, and
`09340b2838ca0e9c9da66bf5daa0fd6e9f192165` remained strict descendants of
the exact source trigger. Targeted attempts 8 and 9 then reran only Navy
FY2025 and FY2026, respectively. Their real executions succeeded; GitHub's
additional same-partition step-less queued/null records are covered by the
owner-approved inert-placeholder exception and are neither executions nor
eligible retry targets.

Run `33145859877` finished attempt 9 successfully. The real Navy FY2026 job
`99257939661` succeeded, reconcile job `99259101821` succeeded, and deploy job
`99262371496` was skipped as required. Attempt 9 has 27 jobs on page 1 and an
empty page 2: 22 successes, four inert queued/null placeholders, and one
skipped deploy. The cumulative `filter=all`, `per_page=100` inventory is
100 + 100 + 15 jobs with page 4 empty. The artifact inventory is 48 unexpired
artifacts with page 2 empty, and the branch run inventory is eight with page 2
empty.

Reconciliation accepted all 20 account-year partitions. Obligation validation,
fast 7/7, rendered 4/4, the 196-case all-account matrix, the 59-case public-link
matrix, and the two-case rendered sentinel matrix passed. Atomic snapshot
commit `521478974ecbeb5b59d11a73d2b90ca065dc270b` contains the exact Army and
Navy stores. Every fiscal-year store total matches its pin; Navy FY2025 equals
the approved canonical File B total, Army plus Navy rolls up exactly to DoD,
and relevant warning arrays are empty. The branch has 49 accounts: the 47
deployed accounts plus these two DoD accounts. The older 51-account expectation
assumed the quarantined Stats/OJP pair and does not apply to this isolated DoD
branch. Commit `174bc2ac78fc3305eaf3ff5c91b08107d6995ebb` then restored the
weekly/all trigger as its only file change with `[skip ci]`.

## Stage 2 scaffold — Air Force and Space Force

The second scaffold appends only `dod/air-force-rdte` (`057-3600`) and
`dod/space-force-rdte` (`057-3620`), their reviewed File A/GTAS pins,
collision-safe Program Activity identities, this handoff evidence, and
dedicated tests. It starts from the sealed Stage 1 weekly/all commit and does
not include either source store or claim source completion.

The official federal-account endpoint was rechecked on 2026-08-31. Air Force
pins for FY2017–FY2026 are `3039261892426`, `3946023359082`,
`4926097145714`, `4966143569342`, `4189223395703`, `4358980604532`,
`5046972337780`, `5092889515726`, `5587181366148`, and `4748612733074`
cents. FY2017 is partial from P06, FY2018–FY2025 are complete, and FY2026 is
partial through P09. Space Force has no account balance before FY2021. Its
FY2021–FY2026 pins are `1052753427202`, `1255327250863`, `1790303171627`,
`2036070402666`, `2004458733008`, and `1740110018139` cents; FY2021–FY2025
are complete and FY2026 is partial through P09.

The official Program Activity inventories returned 31 Air Force rows and 25
Space Force rows on page 1, each with page 2 explicitly empty. Air Force keeps
code-`0007` Operational System Development separate from the exact code-`0007`
`RESEARCH DEVELOPMENT TEST AND EVALUATION AIR FORCE (5 YEAR)` identity, and
keeps code-`00ZX` `UNIDENTIFIED` separate from code-`00ZX` `N/A`. Other exact
`N/A` rows map only to explicit Unknown / other identities. Space Force's PARK
`63Y30LXJBQR` spelling variant maps to the same Advanced Technology Development
identity as PARK `5UW3C6HY83T`; the source PARK remains the authoritative key.
No bare reused code can collapse these reviewed identities.

The exact Stage 2 selector is
`dod/air-force-rdte,dod/space-force-rdte` in `full` mode. Registry availability
yields all FY2017–FY2026 Air Force pins and all FY2021–FY2026 Space Force pins,
including the P09 current-year pins, for 16 serial pull jobs. `full` mode is
required because the two accounts have different first available fiscal years;
the fail-closed custom-range planner correctly rejects an unavailable Space
Force FY2017. Weekly/all remains in place through scaffold publication;
activation is a separate strict-child trigger commit.

Independent Test run `33421456165` exercised the published scaffold at commit
`ee31b59645e0511415b79391046d901aeede7310`. The run and its sole job
`99584573651` are terminal. The job inventory has one record on page 1 and an
explicitly empty page 2; the artifact inventory has one unexpired
`verify-reports` artifact (`9769394592`) on page 1 and an explicitly empty
page 2. Registry validation passed 360/360 and the fast suite passed 7/7. The
rendered suite failed only the eight expected pre-backfill URLs for the two
new account pages and their Basic Research program-activity pages in light and
dark modes; the general obligation matrix, public-link matrix, and rendered
sentinel matrix passed. This expected pre-source failure is evidence that the
registry is published while the two source stores are still absent. The test
run must not be rerun.

### Stage 2 source attempt 1 and exact-key recovery

Source run `33422933441` at trigger commit
`7ee40e54996dcb0505b88ce2f6283f31a8bc06cd` is terminal failure. Its
attempt-specific and cumulative job inventories each contain 19 records on
page 1 and an explicitly empty page 2: the plan and 11 of 16 pull partitions
succeeded, five pull partitions failed at the identity gate, and reconcile and
deploy were skipped. The branch run inventory contains 10 records on page 1
and an explicitly empty page 2. The artifact inventory contains 27 unexpired
artifacts on page 1 and an explicitly empty page 2: normalized plus raw
artifacts for all 11 successful pulls and raw-only artifacts for each failed
pull.

The five raw-only artifacts were retained byte-for-byte and exhaustively
parsed with adapter-equivalent filtering. They contain 13,019 rows in total,
of which 12,931 are relevant to the adapter, and expose exactly the following
five previously unmapped exact keys:

- Air Force FY2020 job `99589659151`, artifact `9771592145`, SHA-256
  `5bb9f2f916ef732f0d1048275a508617d32f579bcab8ce661e95dc99084d8f0e`:
  `OPTN` / `FIELD IS OPTIONAL PRIOR TO FY21` maps to explicit Unknown / other.
  It occurs in 4,526 FY2020 P12 File C rows totaling `39864115830` cents; the
  P12 source total remains `39864115830` cents.
- Air Force FY2022 job `99589659156`, artifact `9772174982`, SHA-256
  `d6126f002f9850b04b4583bba638123dabacd25782d25cce11642fc15db87ccf`:
  malformed `NASO` / `FTWARE AND DIGITAL PILOT PROGRAM` maps to the existing
  Software and Digital Pilot Program identity. It occurs in three FY2022 P05
  File B rows totaling `574556633` cents; the P05 source total remains
  `1463107537710` cents. The same three source positions used canonical code
  `0008` / `SOFTWARE AND DIGITAL PILOT PROGRAM` in P04.
- Space Force FY2021 job `99589659103`, artifact `9774371385`, SHA-256
  `a08bdf831bac1ba22fa9fd876f73a2602e74d72ced73646c307d423aeae6a170`:
  `0099` / `N/A` maps to explicit Unknown / other. It occurs in nine FY2021
  P04 File B rows totaling `27888377017` cents; the P04 source total remains
  `59149399067` cents.
- Space Force FY2022 job `99589660640`, artifact `9774416995`, SHA-256
  `e1d28c646c67f0f82f4e61bfe1fb74f899086c7e94c2c30a5fa3abb012097324`:
  malformed `NAAD` / `VANCED TECHNOLOGY DEVELOPMENT` maps to the existing
  Advanced Technology Development identity. It occurs in three FY2022 P03
  File B rows totaling zero cents; the P03 source total remains
  `272000285775` cents.
- Space Force FY2023 job `99589661403`, artifact `9774520749`, SHA-256
  `4e7f05f494f9ba66638d3280103a3f0f0f865749920b45178f9ab3009d895f26`:
  `00RB` / `REIMBURSABLE PROGRAM` maps to the existing reimbursable identity.
  It occurs in one FY2023 P06 File B row totaling `575` cents; the P06 source
  total remains `1076888034279` cents.

No other exact key is unmapped in the retained failure evidence. These are
collision-checked, exact-key-only identity repairs. They neither alter nor
tolerate source amounts, add synthetic residuals, change File A pins, nor
change the public accounting contract. The five failed partitions must be
retried individually from the latest terminal attempt; the workflow as a whole
must not be rerun.

### Stage 2 sequential recovery evidence

Attempt 2 reran only Air Force FY2020 and its actual execution job
`99657731113` succeeded. Attempt 3 reran only Air Force FY2022 and its actual
execution job `99660621997` succeeded. Attempt 3 is fully terminal: its 19 jobs
occupy page 1 with page 2 explicitly empty (14 success, three copied failures,
and two skipped); the cumulative inventory has 57 jobs on page 1 and an empty
page 2; the artifact inventory has 31 unexpired artifacts on page 1 and an
empty page 2; and the branch-run inventory has 11 runs on page 1 and an empty
page 2.

Attempt 4 reran only the latest-attempt Space Force FY2021 copied failure. Its
actual execution job `99664596938` reached a later exact-key gate after the
previous `0099` / `N/A` repair. Attempt 4 is fully terminal: its 19 jobs occupy
page 1 with page 2 explicitly empty (14 success, three copied failures, and two
skipped); the cumulative inventory has 76 jobs on page 1 and an empty page 2;
the artifact inventory has 32 unexpired artifacts on page 1 and an empty page
2; and the branch-run inventory has 11 runs on page 1 and an empty page 2.

Raw-only artifact `9778038097` is preserved byte-for-byte at SHA-256
`493df01ca1e15fbeb3ee4086141e1ce9d4f0b1be496cefebd81fbdd62ee4c5fd`.
Adapter-equivalent exhaustive parsing of all 143 retained P02-P06 rows exposes
exactly one unmapped key: malformed `NARE` / `IMBURSABLE PROGRAM` with blank
PARK in three FY2021 P06 File B rows totaling `36768447916` cents. This is the
same source-boundary corruption pattern as `NASO` / `FTWARE...` and `NAAD` /
`VANCED...`: the `NA` prefix is joined to the first two letters of the source
label, leaving the remainder in the name field. The exact key therefore maps
to the existing reimbursable identity; the preceding P05 export uses canonical
`0801` / `REIMBURSABLE`. The P06 source total remains `374671835455` cents.
No amount, pin, tolerance, PARK, or synthetic residual changes. The repair is
exact-key-only and collision checked; accepted job `99664596938` must never be
retried.

Attempt 5 reran only Space Force FY2021 after that exact-key repair. Its real
execution job `99668850610` succeeded. The attempt has 19 jobs on page 1 and
an explicitly empty page 2; the cumulative inventory has 95 jobs on page 1
and an empty page 2; the artifact inventory has 34 unexpired artifacts on
page 1 and an empty page 2; and the branch-run inventory has 12 runs on page 1
and an empty page 2.

Attempt 6 reran only Space Force FY2022. Its real execution job `99672615702`
succeeded. Attempt 6 has 20 rows on page 1 and an explicitly empty page 2:
16 successes, one copied failure, two skipped jobs, and inert zero-step queued
placeholder `99672615603`. The cumulative `filter=all`, `per_page=100`
inventory is 100 + 15 jobs with page 3 empty. The artifact inventory has 36
unexpired artifacts with page 2 empty, and the branch-run inventory has 12
runs with page 2 empty.

Attempt 7 reran only Space Force FY2023. Its real execution job `99676527590`
succeeded; `99676527513` is an inert zero-step queued placeholder. The attempt
is terminal failure with 20 rows on page 1 and an explicitly empty page 2:
17 successes, reconcile failure `99679925563`, skipped deploy, and the inert
placeholder. The cumulative inventory is 100 + 35 jobs with page 3 empty.
The artifact inventory has 38 unexpired artifacts with page 2 empty, and the
branch-run inventory has 12 runs with page 2 empty. All five targeted real
Stage 2 pull partitions therefore succeeded.

Reconcile failed only with `dod/space-force-rdte FY2021: complete baseline
changed`. Accepted partition artifact `9778828849` is preserved at SHA-256
`0d5248ce133b85fc8605d40a3c8665cf59b55da04f3dfa90c6c3b015308c1a7a`.
Its accepted P12 provenance has 318 records, normalized total
`1052753427202` cents, and a complete baseline pin for exactly
`1052753427202` cents. The existing registry pin is independently complete at
the same exact total. The failure therefore has zero dollar impact: the
reconciler unconditionally downgraded every first fiscal year to partial even
though the producer correctly preserves an already established complete pin.

The owner approved preserving the established complete Space Force FY2021 pin
on 2026-09-01 UTC. Reconciliation now retains an existing complete or available
first-year pin; its existing fail-closed equality check still rejects any pin
or amount change. Unestablished and partial first years keep the existing
partial-year coercion and material first-period calculation. No amount, pin
value, tolerance, residual, source artifact, or public accounting meaning
changes. Only failed reconcile job `99679925563` may be rerun after this
recovery is published; no accepted pull job or whole workflow is eligible.

## Stage 2 terminal result

Owner-approved recovery commit
`7c926aff30f397fc4af7296e5fb192c083ca44ae` remained the strict child of the
latest exact-key recovery. Attempt 8 then reran only reconcile job
`99679925563`; its real execution `99732023311` succeeded, and deploy job
`99737130651` was skipped as required. No pull partition or whole workflow was
rerun.

Run `33422933441` finished attempt 8 successfully. The attempt-specific
inventory has 19 jobs on page 1 and an explicitly empty page 2: plan, all 16
pulls, and reconcile succeeded, while deploy was skipped. The cumulative
`filter=all`, `per_page=100` inventory is 100 + 54 jobs with page 3 empty. Its
only queued/null rows are owner-approved inert placeholders `99672615603` and
`99676527513`; neither represents an execution or eligible retry target. The
artifact inventory has 38 unexpired artifacts with page 2 empty, and the
branch-run inventory has 13 runs with page 2 empty.

Reconciliation accepted all 16 account-year partitions. Obligation
validation, fast 7/7, rendered 4/4, the 204-case all-account matrix, the
59-case public-link matrix, and the two-case rendered sentinel matrix passed.
Atomic snapshot commit `207c02b16c2a3b1f15f1faef693c9e8955587d5f`
contains the exact Air Force and Space Force stores. Every fiscal-year total
matches its pin, the Space Force FY2021 complete pin remains exactly
`1052753427202` cents, account and DoD rollups are exact, and relevant warning
arrays are empty. The isolated branch has 51 accounts: the 47 deployed
accounts plus four completed DoD accounts. Commit
`0a0bb8942863895e24a4dc34249b99c8237c3ff7` then restored weekly/all as its
only file change with `[skip ci]`.

## Stage 3 scaffold — Defense-Wide and Defense Health Program

The final scaffold appends only `dod/defense-wide-rdte` (`097-0400`) and
`dod/defense-health-program` (`097-0130`), their reviewed File A/GTAS pins,
collision-safe Program Activity identities, this handoff evidence, and
dedicated tests. It starts from the sealed Stage 2 weekly/all commit and does
not include either source store or claim source completion.

DARPA is included within Defense-Wide RDT&E (`097-0400`), not a standalone
account total. The full Defense-Wide account includes DARPA and other Defense
Agencies activity and therefore must not be labeled as DARPA. DHP remains its
own `097-0130` account.

The official federal-account endpoint was rechecked on 2026-09-01 UTC.
Defense-Wide pins for FY2017–FY2026 are `2251362677352`, `2457216636704`,
`2645819709252`, `2710538880746`, `2875140199888`, `2943303100353`,
`3507738978109`, `3845905263059`, `3813645882772`, and `3644905851774`
cents. DHP pins are `3735497424800`, `3815667849023`, `3945894755468`,
`4144696246716`, `4047318547619`, `4178537884292`, `4401952664476`,
`4571628570276`, `4692069313553`, and `4108805214110` cents. For both
accounts, FY2017 is partial from P06, FY2018–FY2025 are complete, and FY2026
is partial through P09.

The official Program Activity inventories returned 47 Defense-Wide rows and
45 DHP rows on page 1, each with page 2 explicitly empty. PARK remains the
authoritative identity. Exact historical code/name pairs remain separate when
codes were reused: for example, Defense-Wide code `0004` distinguishes
Advanced Component Development and Prototypes, the DOD/VA Incentive Fund, and
`N/A`; DHP code `0001` distinguishes Operation and Maintenance, Basic
Research, Major Equipment, Operating Forces, Procurement, Reimbursable
Program, and `N/A`. Every reviewed row resolves through a PARK or exact
code/name key, and no bare reused code can collapse those identities.

The exact Stage 3 selector is
`dod/defense-wide-rdte,dod/defense-health-program` in `full` mode. Registry
availability yields FY2017–FY2026 for both accounts, including P09 current-year
pins, for 20 serial pull jobs. Weekly/all remains in place through scaffold
publication; activation must be a separate strict-child trigger commit. The
Stage 3 source graph must remain isolated until terminal and uses the same
one-exact-latest-attempt-job recovery discipline as Stages 1 and 2.

The independent scaffold Test run `33471397410` at published scaffold commit
`fd7484ede3065d2736e7cfbd7fd5791c05af9ea9` is terminal. Its only job
`99741711960` passed compilation/JSON, registry, the complete fast tier
(`7/7`), the five-case obligation matrix, the 59-case public-link matrix, and
the two-case sentinel matrix. The rendered all-account matrix failed only on
the eight expected pre-store URLs: the Defense-Wide account and Basic Research
pages plus the DHP account and Operation and Maintenance pages, each in light
and dark modes. Each failure was the expected `404` for a dashboard store that
does not exist before the source backfill. The job listing contains one row on
page 1 and an explicitly empty page 2. Artifact `9786869460`
(`verify-reports`, unexpired, 3923 bytes) is the only artifact on page 1 and
artifact page 2 is explicitly empty. The retained artifact ZIP digest reported
by the job is
`65027f60c5abed4956aaf51a61cff5dcacc3a2347b0b847aed88a3d5fe58cc58`.
This Test run is final and must not be rerun.

Stage 3 source run `33472362131` at trigger
`f871fbd4cab5efac91499beb19862525defe1ce7` planned exactly 20 serial
partitions. Attempt 1 DHP FY2017 job `99744617364` accepted the official P06
File B snapshot with 125 rows, then stopped on one previously unseen exact
historical label: code `0002`, blank PARK, name
`RESEARCH, DEVELOPMENT, TEST, & EVALUATION`. Raw artifact `9786973589` is
preserved at `/private/tmp/dod-dhp-fy2017-attempt1.zip` with SHA256
`014905d96c1f767d95d3c0b45e05ca78a8d1368bcf38d76575c11c3f443fee96`.
An exhaustive parse found 12 unique exact keys and no other unmapped key. The
new label totals `35790750341` cents at P06 and maps to the existing
`research-development-test-evaluation` identity; the complete P06 File B
snapshot remains exactly `1807576647850` cents. This is an exact-key identity
repair only: it changes no source row, pin, total, tolerance, or residual.
Recovery must remain local until every real attempt-1 source job is terminal.

Attempt 1 DHP FY2019 job `99744617286` accepted the official P03 File B
snapshot with 129 rows, then stopped on one exact historical label: code
`008B`, blank PARK, name `DEFENSE HEALTH PROGRAM`. Raw artifact `9787349671`
is preserved at `/private/tmp/dod-dhp-fy2019-attempt1.zip` with SHA256
`cfcac4d93437f5289e566f9bfa69157f8c9e346c20514711ed0920aa8760433b`.
An exhaustive parse found 13 unique exact keys and no other unmapped key. The
label totals `1433217270` cents at P03; the complete P03 File B snapshot totals
`1420514789985` cents. On 2026-09-01 the owner approved the exact-preservation
contract: a standalone source identity with slug `defense-health-program`,
code `008B`, and name `DEFENSE HEALTH PROGRAM`, with no change to any source
row, pin, total, tolerance, or residual.

Attempt 1 DHP FY2025 job `99744617337` accepted every P02-P12 File B
snapshot and the P12 File C export, then stopped at the exact source-total
gate. Raw artifact `9788896971` is preserved at
`/private/tmp/dod-dhp-fy2025-attempt1.zip` with SHA256
`7ec29f76839814162b1017bd9be0f3750b62b4d74ef56c414dc62257a00b886b`.
Adapter-equivalent exhaustive parsing found no unmapped exact key. The
retained P12 File B total is `4676524125773` cents. A separate official,
date-filtered Program Activity endpoint request returned 22 rows on page 1,
an explicitly empty page 2, and the same exact `4676524125773`-cent total.
The retained endpoint pages are
`/private/tmp/dod-dhp-fy2025-program-activities.json` (SHA256
`818405fd14dbad2e39b072442cc88470ef088080836a86010712d0c83918f368`)
and `/private/tmp/dod-dhp-fy2025-program-activities-page2.json` (SHA256
`00d9c9fb9040bed5b63e0b50845625e934b7b75328340b464cd277bce2960cb4`).
The reviewed official GTAS/File A pin remains `4692069313553` cents, so File A
minus File B is exactly `15545187780` cents (`$155,451,877.80`). On 2026-09-01
the owner approved preserving File A and canonical File B as two exact official
totals under the existing dual-pin/source-warning contract, with an exact
variance-ledger entry and no tolerance or synthetic residual.

Attempt 1 DHP FY2020 job `99744617369` accepted all P02-P12 File B
snapshots and the P12 File C export, then stopped on the established pre-FY2021
placeholder `OPTN` / `FIELD IS OPTIONAL PRIOR TO FY21` with blank PARK. Raw
artifact `9787694836` is preserved at
`/private/tmp/dod-dhp-fy2020-attempt1.zip` with SHA256
`15108d6dcae470d700a5a946e91fe3f7b4c056661ab1a05cc7e80dc3fe3cd306`.
Adapter-equivalent exhaustive parsing found no unmapped File B key; among
10,636 nonblank-amount File C rows it found exactly that one unmapped key,
totaling `319267192516` cents. The complete File C total is
`638897009542` cents and the P12 File B total remains exactly
`4144696246716` cents. The placeholder maps to explicit `unknown-other`, the
same contract already established for Army and Navy. No source row, pin,
total, tolerance, PARK, or residual changes.

Attempt 1 DHP FY2021 job `99744617351` accepted P02-P06 and stopped on the
malformed exact key `NARE` / `IMBURSABLE PROGRAM` with blank PARK. Raw artifact
`9787761673` is preserved at `/private/tmp/dod-dhp-fy2021-attempt1.zip` with
SHA256 `06c9c992f5385ebbe43a760fe70aa7ff5af13155cd9bb0e1eb6c9feffcc4f224`.
Exhaustive parsing found exactly that one unmapped P06 key in 163 rows and
eight exact keys, totaling `-102355` cents; the P06 File B total remains
`2165744325047` cents. This is the same source-boundary corruption already
reviewed for Space Force and maps to the existing reimbursable identity. No
source row, pin, total, tolerance, PARK, or residual changes.

Attempt 1 DHP FY2023 job `99744617355` accepted P02-P03 and stopped on the
spacing-loss variant code `0002`, name `RESEARCH DEVELOPMENTTESTEVALUATION`,
blank PARK. Raw artifact `9788145439` is preserved at
`/private/tmp/dod-dhp-fy2023-attempt1.zip` with SHA256
`9493ba84d378cf8fe1f69d30f199b7d7be3d9bac3a723230c241dd49b2a7f0e3`.
Exhaustive parsing found exactly that one unmapped P03 key in 207 rows and 22
exact keys, totaling `530073` cents; the P03 File B total remains
`1060219630625` cents. It maps to the existing
`research-development-test-evaluation` identity. No source row, pin, total,
tolerance, PARK, or residual changes. All three exact-key recoveries remain
local until every real attempt-1 source job is terminal.

Attempt 1 DHP FY2026 job `99744617378` accepted P02 and P03, then stopped on
the exact PARK-only key `5Q03E54NTZ6` with blank code and name. Raw artifact
`9788930625` is preserved at `/private/tmp/dod-dhp-fy2026-attempt1.zip` with
SHA256 `b3e3023436db32fbf6f8ca5f41730fcb921af8525d2ada19b83716d65420d261`.
Exhaustive parsing found seven exact P03 keys and only this key unmapped; it
totals `13824014403` cents, while the complete P03 File B snapshot totals
`1198476540459` cents. The official DHP Program Activity inventory returned
45 rows on page 1 and an explicitly empty page 2, but contains no identity for
this PARK. Those retained pages are
`/private/tmp/dod-dhp-program-activities-current.json` (SHA256
`d6277ad96bf4129dd0ac9624f270608cd4683f6a4005888166609ebae7541eb8`) and
`/private/tmp/dod-dhp-program-activities-current-page2.json` (SHA256
`222ce99283057c137110933cb8ab3e6c4538a3b91d44841104be9574d473cc97`).
On 2026-09-01 the owner approved representing this `$138,240,144.03`
blank-label activity as the standalone neutral PARK-keyed identity
`source-label-unavailable-5q03e54ntz6`. The display name states only that the
source label is unavailable and does not infer program meaning. No source row,
pin, total, tolerance, or residual changes.

Attempt 1 Defense-Wide FY2017 job `99744617489` accepted the official P06
File B snapshot with 238 rows, then stopped on exact code `00CA`, blank PARK,
name `CLOSED ACCOUNT`. Raw artifact `9788947797` is preserved at
`/private/tmp/dod-defense-wide-fy2017-attempt1.zip` with SHA256
`0491874c8f59fc8347936b77954eadcac8292d96835efd70f360ef291b4f1aa8`.
Exhaustive parsing found 16 exact keys and only this key unmapped; it totals
`11429745` cents and the P06 File B snapshot remains exactly `980116494804`
cents. The exact source label maps to the existing
`closed-account-adjustment` identity alongside code `00CA` / `CLOSED ACCOUNT
ADJUSTMENT`. This is an exact-key identity repair only and changes no source
row, pin, total, tolerance, PARK, or residual. Recovery remains local until
every real attempt-1 source job is terminal.

Attempt 1 Defense-Wide FY2020 job `99744618307` accepted all P02-P12 File B
snapshots and the P12 File C export, then stopped on the established pre-FY2021
placeholder `OPTN` / `FIELD IS OPTIONAL PRIOR TO FY21` with blank PARK. Raw
artifact `9790299817` is preserved at
`/private/tmp/dod-defense-wide-fy2020-attempt1.zip` with SHA256
`7a3d70d692879214fec48e589950b130508f3d5fa54800f7dd52ac2948437ff3`.
Adapter-equivalent exhaustive parsing found no unmapped File B key; among
7,941 nonblank-amount File C rows it found exactly that one unmapped key,
totaling `118057611865` cents. The complete File C total is `687143635686`
cents and the P12 File B total remains exactly `2710538880746` cents. The
placeholder maps to explicit `unknown-other`, the same contract already used
for Army, Navy, and DHP. No source row, pin, total, tolerance, PARK, or
residual changes.

Attempt 1 Defense-Wide FY2021 job `99744618317` accepted P02-P06 and stopped
on the exact source-boundary corruption `NAMI` / `SCELLANEOUS` with blank
PARK. Raw artifact `9790393234` is preserved at
`/private/tmp/dod-defense-wide-fy2021-attempt1.zip` with SHA256
`e96cabe63c9a8a8548cc2f63a17fb03995a0eaba446e303d8522a0f94e39c7db`.
Exhaustive parsing found exactly that one unmapped P06 key in 234 rows and 12
exact keys, totaling `45000000` cents; the P06 File B total remains
`1482792692169` cents. `NA` has absorbed the first two letters of
`MISCELLANEOUS`, the same reviewed boundary-corruption pattern as DHP and
Space Force reimbursable labels, so the exact key maps to the existing
`miscellaneous` identity. No source row, pin, total, tolerance, PARK, or
residual changes.

Attempt 1 Defense-Wide FY2022 job `99744618350` stopped at P02 on the same
exact `NAMI` / `SCELLANEOUS` source-boundary corruption. Raw artifact
`9790413421` is preserved at `/private/tmp/dod-defense-wide-fy2022-attempt1.zip`
with SHA256 `588cca416cd72fece95a12f7ff690add9be7241712ee4baffe11e7d3bd3ac903`.
Exhaustive parsing found exactly that one unmapped P02 key in 225 rows and 12
exact keys, totaling `132459489` cents; the P02 File B total remains
`244709809729` cents. The shared exact alias maps it to the existing
`miscellaneous` identity without changing any source row, pin, total,
tolerance, PARK, or residual. All Defense-Wide exact-key recoveries remain
local until every real attempt-1 source job is terminal.

Attempt 1 Defense-Wide FY2023 job `99744618294` accepted every P02-P12 File B
snapshot and the P12 File C export, then stopped at the exact source-total
gate. Raw artifact `9790896334` is preserved at
`/private/tmp/dod-defense-wide-fy2023-attempt1.zip` with SHA256
`41515034d1103a432e276a0ddfad1ef5e5aae4bac482973408eb446da0ddc84b`.
Adapter-equivalent exhaustive parsing found no unmapped exact key. The
retained P12 File B total is `3507738877251` cents. A separate official,
date-filtered Program Activity endpoint request returned 28 rows on page 1,
an explicitly empty page 2, and the same exact `3507738877251`-cent total.
The retained endpoint pages are
`/private/tmp/dod-defense-wide-fy2023-program-activities.json` (SHA256
`32cdaed1c1acf5e7edc54e4f38478490ccd255c9d32838e61f0d9d47c1e21af8`)
and `/private/tmp/dod-defense-wide-fy2023-program-activities-page2.json`
(SHA256 `e94f2d2dc2c74024a1f7fb860c2335dc12c3c9294eb19174155544ee91f04e2f`).
The reviewed official GTAS/File A pin is `3507738978109` cents, so File A
minus File B is exactly `100858` cents (`$1,008.58`). On 2026-09-01 the owner
approved preserving File A and canonical File B as two exact official totals
under the existing dual-pin/source-warning contract, with an exact
variance-ledger entry and no tolerance or synthetic residual. DARPA is included
within federal account `097-0400`; this evidence and pin cover the complete
Defense-Wide account and do not label all Defense-Wide activity as DARPA.

Attempt 1 Defense-Wide FY2025 job `99744618422` accepted P02 and stopped on
exact code `0030`, blank PARK, name `N/A`. Raw artifact `9791410259` is
preserved at `/private/tmp/dod-defense-wide-fy2025-attempt1.zip` with SHA256
`7eed224b5d3163d7c241c7f67705a2972b58860f1444d4013b25895848af975f`.
Exhaustive parsing found 26 exact P02 keys and only this key unmapped; it
totals `25000000` cents, while the P02 File B snapshot remains exactly
`508315589931` cents. The explicit `N/A` label maps to the established
`unknown-other` identity alongside the reviewed Defense-Wide N/A inventory.
This is an exact-key repair only and changes no source row, pin, total,
tolerance, PARK, or residual. Recovery remains local until every real
attempt-1 source job is terminal.

Attempt 1 is fully terminal. Run `33472362131` completed with failure after
all 20 real serial pull partitions reached terminal state. The
attempt-specific authenticated inventory contains 23 jobs on page 1 and an
explicitly empty page 2: plan and seven pull partitions succeeded, 13 pull
partitions failed on the exact recoveries and owner gates documented above,
and reconcile/deploy were skipped. The cumulative `filter=all`,
`per_page=100` inventory is likewise 23 jobs on page 1 with page 2 empty.
Artifact inventory contains 27 unexpired artifacts on page 1 with page 2
empty, and the branch inventory contains 15 runs on page 1 with page 2 empty.
No attempt-1 job is nonterminal and no inert placeholder is present in this
attempt. On 2026-09-01 the owner approved all four remaining Stage 3 gates:
the exact DHP FY2019 identity, the neutral DHP FY2026 PARK identity, and the
DHP FY2025 and Defense-Wide FY2023 dual pins. The combined recovery may be
published only after all local gates and exhaustive raw post-audits pass; no
job may be retried before that publication is verified.

After approval, an adapter-equivalent exhaustive post-audit reverified the
outer SHA256 and ZIP CRC for all 13 retained failed-partition archives and
resolved all 46,977 source rows that require Program Activity identity lookup.
Every archive reports zero unmapped keys under the combined recovery. The
audit changes no retained raw byte or source amount; it verifies only that the
approved registry maps the preserved evidence without collision or fallback.

The approved combined recovery was published as commit
`a59f0befbac5dbb2479783836cc057d042ab2f70`, tree
`83cb8f7bd460e980ff76ad640f4ae77988df0b52`, a strict child of Stage 3 trigger
`f871fbd4cab5efac91499beb19862525defe1ce7`. The trigger blob remains exactly
`d9eaadbfc12c90ec8bd7d29440a7005db59062dc`. The recovery changes exactly the
registry, this handoff, the source-variance handoff and machine ledger, the two
Stage 3 baseline files, and the focused DoD test. Focused tests passed 31/31,
registry validation passed 374/374, fast tests passed 7/7, and JSON, diff, and
the exhaustive retained-raw audit were green. Independent recovery Test run
`33514647666` then passed every non-rendered gate and failed only on the eight
expected pre-store Defense-Wide and DHP 404 URLs. Its sole unexpired artifact
is `9803537757`; jobs and artifacts each had an explicitly empty page 2. That
test run is separate from the source graph and must not be rerun.

Source run `33472362131` attempt 2 reran only the exact current-attempt DHP
FY2017 failure. Its new execution job `99878764394` succeeded. Attempt 2 then
reached a fully terminal state with 23 attempt-specific jobs on page 1 and an
explicitly empty page 2: nine success, 12 copied failures, and reconcile and
deploy skipped. The cumulative inventory contained 46 jobs with the next page
empty, the artifact inventory contained 29 unexpired artifacts with page 2
empty, and the branch inventory contained 16 runs with page 2 empty. No job
was nonterminal.

Attempt 3 reran only the exact attempt-2 DHP FY2019 copied failure. Its new
execution job `99882395063` checked out recovery commit
`a59f0befbac5dbb2479783836cc057d042ab2f70`, accepted P02 through P09, and
stopped at P09 on exact code `0020`, blank PARK, name `UNKNOWN/OTHER`. Raw
artifact `9803737577` is preserved at
`/private/tmp/dod-dhp-fy2019-attempt3.zip` with SHA256
`8c32377e3b5cf2e0dc56d21d9df8852ebd0151b87979c8bcc7e20edeb7d5adf9`,
matching GitHub's digest. Exhaustive parsing of all retained P02-P09 pages
found exactly that one unmapped key: two P09 rows totaling `61952301` cents.
The P09 File B total remains exactly `2809688986544` cents. The exact
`UNKNOWN/OTHER` label maps to the established `unknown-other` identity; this
is an agent-authorized exact-key recovery and changes no source row, pin,
total, tolerance, PARK, or residual.

Attempt 3 is fully terminal. The authenticated latest-attempt inventory has
23 jobs on page 1 and an explicitly empty page 2: nine success, 12 failure,
and reconcile and deploy skipped. The cumulative inventory has 69 jobs and an
empty next page, artifacts have 30 unexpired entries and an empty page 2, and
the branch has 16 runs and an empty page 2. No job is nonterminal. Publish the
three-file exact-key recovery only as a strict child of `a59f0bef...`, with
the Stage 3 trigger blob unchanged, after all local gates and a post-audit of
the retained attempt-3 raw artifact pass. Then rerun only the exact latest-
attempt DHP FY2019 failed job once; do not advance to DHP FY2020 first.

That follow-up exact-key recovery was published as commit
`809e6f61b37f92a2f8a961613393ac3e82b7dca8`, tree
`e6512288cec8a872cac9b493dd8a550e7274522c`, a strict child of
`a59f0befbac5dbb2479783836cc057d042ab2f70`. It changes exactly the registry,
this handoff, and the focused DoD test; the Stage 3 trigger blob remains
`d9eaadbfc12c90ec8bd7d29440a7005db59062dc`. Local JSON and diff checks,
DoD 16/16, reconcile/validation 15/15, registry 374/374, fast 7/7, and the
attempt-3 raw post-audit were green. Independent Test run `33517520837` is
terminal failure only on the same eight expected pre-store Defense-Wide and
DHP rendered 404 URLs; its registry and fast gates passed. It has one job and
one unexpired artifact, `9804729116`, with jobs and artifacts page 2 empty.
Never rerun that Test.

Source attempt 4 reran only DHP FY2019, whose new execution job
`99892820843` succeeded. Its terminal attempt inventory was 23 jobs plus an
empty page 2: ten success, 11 copied failures, and reconcile and deploy
skipped. Cumulative jobs were 92 plus an empty page 2, artifacts were 32 and
all unexpired plus an empty page 2, and branch runs were 17 plus an empty page
2. Attempt 5 reran only DHP FY2020, whose new execution job `99898374359`
succeeded. Its terminal attempt inventory was 23 jobs plus an empty page 2:
11 success, ten copied failures, and reconcile and deploy skipped. Cumulative
jobs were 100 plus 15 plus an empty page 3, artifacts were 34 and all
unexpired plus an empty page 2, and branch runs page 2 was empty.

Source attempt 6 reran only DHP FY2021, whose new execution job
`99904790377` succeeded. Its fully terminal inventory has 23 attempt jobs and
an explicitly empty page 2: 12 success, nine copied failures, and reconcile
and deploy skipped. Cumulative jobs are 100 plus 38 plus an empty page 3;
artifacts are 36 and all unexpired plus an empty page 2; branch runs are 17
plus an empty page 2. No job is nonterminal.

Attempt 7 reran only DHP FY2023. Its new execution job `99911391883`
accepted P02 through P10, then stopped on the exact spacing variant code
`0002`, blank PARK, name `RESEARCH  DEVELOPMENT  TEST &  EVALUATION`. Raw
artifact `9807493441` is preserved at
`/private/tmp/dod-dhp-fy2023-attempt7.zip` with SHA256
`bc9dba347910bfce5297293133db69977801a2607e8f4ae5f7a57107ff6644e9`,
matching GitHub's digest, and its outer and nested ZIP CRCs pass. Exhaustive
P02-P10 parsing found exactly that one unmapped key: three P10 rows totaling
`1912432` cents. The P10 File B total remains exactly `3600872654596` cents.
The spacing-only source label maps to the established
`research-development-test-evaluation` identity; this is an agent-authorized
exact-key recovery and changes no source row, pin, total, tolerance, PARK, or
residual.

Attempt 7 is fully terminal. Its authenticated latest-attempt inventory has
23 jobs and an explicitly empty page 2: 12 success, nine failure, and
reconcile and deploy skipped. Cumulative jobs are 100 plus 61 plus an empty
page 3, artifacts are 37 and all unexpired plus an empty page 2, and branch
runs are 17 plus an empty page 2. No job is nonterminal. Publish this
three-file exact-key recovery only as a strict child of `809e6f61...`, with
the Stage 3 trigger blob unchanged, after all local gates and a post-audit of
the retained attempt-7 raw artifact pass. Then rerun only the exact latest-
attempt DHP FY2023 failed job once; do not advance to DHP FY2025 first.

That exact-key recovery was published as commit
`49915956f9d683f9b88ebf5f1e27c0596f1381a1`, tree
`132bdaa67231b594b3e053d8e413a58b6f666693`, a strict child of
`809e6f61b37f92a2f8a961613393ac3e82b7dca8`. It changes exactly the registry,
this handoff, and the focused DoD test; the Stage 3 trigger blob remains
`d9eaadbfc12c90ec8bd7d29440a7005db59062dc`. Local JSON and diff checks,
DoD 17/17, reconcile/validation 15/15, registry 374/374, fast 7/7, and the
attempt-7 raw post-audit were green. Independent Test run `33526494898` is
terminal failure only on the same eight expected pre-store Defense-Wide and
DHP rendered 404 URLs. Never rerun that Test.

Attempt 8 reran only DHP FY2023; real execution job `99923532872` succeeded.
Attempt 9 reran only DHP FY2025; real execution job `99929128861` succeeded.
Attempt 10 reran only DHP FY2026; real execution job `99933377949` succeeded.
Attempt 11 reran only Defense-Wide FY2017; real execution job `99938393568`
succeeded. Each attempt was fully terminal and completely inventoried before
the next exact latest-attempt failed job was rerun. Copied terminal records
were not counted as executions.

Attempt 12 reran only Defense-Wide FY2020. Real job `99941937017` completed
success with all nine steps green. Rows `99941937038` and `99941937361`
remained queued/null even though each contained the same nine completed-
success steps, including byte-identical names, statuses, conclusions, and
timestamps. The run was terminal, and the owner approved these two exact rows
as inert aliases of `99941937017`. They are documented here, are not counted
as executions, and must never be rerun.

The owner subsequently approved a narrow reusable success-case inert-alias
contract. A queued/null row may be treated as an inert alias only when the
workflow run is terminal, exactly one same-partition row is completed/success,
the alias's entire completed step array (names, statuses, conclusions, and all
timestamps) is byte-identical to that successful row, artifact names and
cardinality show exactly one normalized-plus-raw output pair for the
partition, and the alias is documented, never counted as an execution, and
never rerun. Under that exact contract, attempt 13 Defense-Wide FY2021 real
job `99954172706` succeeded and rows `99954172358` and `99954172401` are inert
aliases; its sole output pair is normalized artifact `9812770792` and raw
artifact `9812771320`. Attempt 14 Defense-Wide FY2022 real job `99963508288`
succeeded and row `99963508058` is an inert alias; its sole output pair is
normalized artifact `9813818333` and raw artifact `9813819158`. Attempt 15
Defense-Wide FY2023 real job `99969933018` succeeded and rows `99969932614`,
`99969932644`, and `99969932762` are inert aliases; its sole output pair is
normalized artifact `9814280735` and raw artifact `9814281555`. Each run was
terminal before the next exact current-attempt failed job was rerun.

Attempt 16 reran only Defense-Wide FY2025. The real job `99974200547`
accepted P02 through P12 and then failed at the exact source-total pin gate:
current P12 File B is `3812362307540` cents while the existing official
GTAS/File A pin is `3813645882772` cents. Raw artifact `9814928296` is
preserved at `/private/tmp/dod-defense-wide-fy2025-attempt16.zip` with SHA256
`72c1d5417fc851f2320387639c77b203d97df269fd1bb54f67b1771d185b63f5`;
the nested P12 File B ZIP SHA256 is
`b8937e70d56ce14c73691ae01839560e97928a840916d23b5d7ce41013619579`.
Adapter-equivalent exhaustive parsing found zero unmapped keys and exactly
`3812362307540` cents. A separate official date-filtered Program Activity
request returned 26 rows on page 1, an explicitly empty page 2, and the same
exact total. Those pages are preserved as
`/private/tmp/dod-defense-wide-fy2025-program-activities-attempt16.json`
(SHA256 `8aeba04e65598ca0c3c524d7340945930d5bdcd52aff1b6d9da7226571178950`)
and its page-2 response (SHA256
`e7ade28c7cfb4c39bb3c515aff94e5ab0d207e7c48dd763b12043666a248c422`).
The official federal-account/GTAS File A response is preserved as
`/private/tmp/dod-defense-wide-fy2025-federal-account-attempt16.json` with
SHA256 `29246cee27412be8095e927c289373c72daef91122acab75830b8d170f3384c7`.
File A minus canonical File B is exactly `1283575232` cents
(`$12,835,752.32`). On 2026-09-01 the owner approved preserving both exact
official totals under the dual-pin/source-warning contract, with no tolerance
or synthetic residual. DARPA is included within federal account `097-0400`;
this evidence covers the complete Defense-Wide account and does not label all
Defense-Wide activity as DARPA.

Attempt 16 is fully terminal. Its latest-attempt inventory contains 25 rows on
page 1 and an explicitly empty page 2: 20 success, the one real FY2025
failure, reconcile and deploy skipped, and two queued/null envelopes. The
cumulative inventory is 100 plus 100 plus 100 plus 78 rows and an empty page
5. Artifacts total 54, all unexpired, with an empty page 2; branch runs total
18 with an empty page 2. Rows `99974200153` and `99974200296` have completed
step arrays byte-identical to failed real job `99974200547`, and attempt 16
created exactly one raw artifact and no normalized artifact. On 2026-09-01
the owner approved these two exact rows as inert aliases under this narrow
failure-case evidence only. They are not executions, must never be counted or
rerun, and do not establish a broader failed-run rule.

The approved FY2025 dual pin, variance ledger, focused test, and this evidence
record passed all local gates. DoD tests passed 16/16,
reconcile/validation passed 15/15, registry validation passed 374/374, and the
full unit suite passed 260 tests with one expected skip. The remaining fast-
tier validators all passed: obligations, NIH, USAspending calibration,
funding sentinel, DMS baseline, and award invariants. JSON and diff checks are
green, and an adapter-equivalent exhaustive post-audit reverified all 14
retained raw archives with zero unmapped keys. Publish exactly this five-file
recovery as one strict child of
`49915956f9d683f9b88ebf5f1e27c0596f1381a1` with the Stage 3 trigger blob
unchanged. Re-inventory the fully terminal graph immediately before action,
then rerun exactly current-attempt real failed job `99974200547` once. Never
submit either alias row and never rerun the workflow as a whole.

That recovery was published as commit
`66fc1c1530d4ca1dc5739414a1250032054c583d`, tree
`d6f881f4882fd770cb765e51f8330ca3357c3575`, a strict child of
`49915956f9d683f9b88ebf5f1e27c0596f1381a1`. It changes exactly the
Defense-Wide baseline, exact source-variance ledger, source-variance
documentation, this handoff, and the focused DoD test. The Stage 3 trigger
blob remains `d9eaadbfc12c90ec8bd7d29440a7005db59062dc`.

After a fresh fully terminal attempt-16 inventory, exact real failed job
`99974200547` was accepted for rerun once. Attempt 17 real Defense-Wide FY2025
job `100013963202` completed success with all nine steps green. Row
`100013963389` is an inert alias under the owner-approved reusable success
contract: the run is terminal, exactly one same-partition execution completed
success, its complete step array is byte-identical to the real job, and the
attempt created exactly one normalized artifact (`9819344250`) plus one raw
artifact (`9819345197`). The alias is not an execution and must never be
counted or rerun.

Attempt 17 is fully terminal failure. Its latest-attempt inventory has 24 jobs
on page 1 and an explicitly empty page 2: 21 success, reconcile failure,
deploy skipped, and the one approved inert alias. Cumulative jobs are 100 plus
100 plus 100 plus 100 plus two rows and an empty page 6. Artifacts total 56,
all unexpired, with an empty page 2; branch runs total 19 with an empty page
2. Reconcile job `100017108317` passed atomic reconciliation and full
53-account store, baseline, provenance, freshness, and dashboard validation.
It failed only in the fast unit-test step because
`test_stage_three_preserves_exact_file_a_pins` froze current partial FY2026 to
the scaffold-time amounts. The accepted artifacts correctly refreshed
Defense-Wide FY2026 from `3644905851774` to `3644486509517` cents and DHP
FY2026 from `4108805214110` to `3886854960283` cents. All complete-year pins
through FY2025, including both approved FY2025 dual pins, remained exact.

On 2026-09-01 the owner approved a minimal test-only correction: retain exact
pin assertions for historical FY2017-FY2025 and explicit complete status for
FY2018-FY2025, while asserting FY2026 as a source-refreshable partial year
through P09 with an integer source-derived amount rather than freezing its
scaffold-time value. This changes no production logic, source data, baseline
amount, dual pin, variance ledger, tolerance, residual, or workflow trigger.
The production contract remains unchanged: accepted current partial
partitions advance the dashboard through the latest released submission
period, while completed years fail closed on any pin change.

The correction passed the focused DoD and reconciliation suite (20/20), then
the full fast tier: 260 unit tests with one expected skip, obligation-ledger
validation, NIH validation, USAspending calibration, funding-sentinel
validation, DMS baseline verification, and award invariants (7/7 checks).
JSON and diff checks are green. The exact delta from published parent
`66fc1c15...` is only this handoff plus `tests/test_obligations_dod.py`; the
workflow trigger and every production, source, baseline, pin, and ledger file
remain byte-identical.

That test-only correction was published as
`fda1be79d22fd59eacd02cc265be96ccdbfc692e`, tree
`6902d2e2abe54ea9c460e8cf4cc91c69cfd3f2a0`, a strict child of
`66fc1c1530d4ca1dc5739414a1250032054c583d`. After a fresh terminal
attempt-17 inventory, exact current-attempt reconcile job `100017108317` was
accepted for rerun once. Attempt 18 reconcile job `100038084744` completed
success with all 16 steps green, including the atomic snapshot, full
53-account obligation validation, fast tier, and rendered tier. The workflow
completed success and deploy was skipped. The latest-attempt inventory has 23
completed rows on page 1 and an explicitly empty page 2: 22 success and one
deploy skip, with no nonterminal or inert rows. Cumulative jobs occupy 100,
100, 100, 100, and 25 rows followed by an empty page 6. Artifacts total 56,
all unexpired, with an empty page 2; branch runs total 20 with an empty page
2.

The resulting atomic snapshot is
`640af0afd0ebb53508c2b34bf7769cf471c58c28`, tree
`b52d3d34378517f23522405f7bfd6e3c22f452ca`, a strict child of the
test-only recovery. It changes exactly 83 generated data files and the two
Stage 3 baselines. DHP FY2025 remains complete with File A
`4692069313553`, canonical File B `4676524125773`, and exact variance
`15545187780` cents. Defense-Wide FY2025 remains complete with File A
`3813645882772`, canonical File B `3812362307540`, and exact variance
`1283575232` cents. There is no tolerance or synthetic residual. Both FY2026
baselines are partial through P09 and match their accepted store endpoints:
DHP `3886854960283` cents and Defense-Wide `3644486509517` cents. Both
account dashboards end at `FY2026P09`, contain no warnings, and roll up
exactly. The registry contains 53 integrated accounts. Commit
`c33c1de0697fb6619acc866048d40e5d491a02d5`, tree
`97dbd0bde6a6e72f816798d90e9ec355d3b0fe97`, is the strict one-file
`[skip ci]` child restoring the obligation trigger to `weekly` / `all`.

Final integration starts from that sealed Stage 3 commit and current main
`6f94a81e25451453445ace9f72c90e0f14742b17`, whose merge base is
`b7753ab1c598c7cad8c7e7251ddffe3067c510fe`. The three-way merge was clean.
Current main contained all 87 per-unit commits from scheduled Update data run
`33417507401`, but that run's rollup failed live NIH reconciliation before it
could commit the regenerated parent dashboards. The exact merge therefore
initially exposed a stale NIH root (`711155`) against its updated leaf union
(`712005`). It also exposed two exact records already covered by the approved
RePORTER retraction ledger: `nih:11462449` in NIA and `nih:11555862` in
NIEHS. No new retraction judgment was made. Those two ledger records were
removed mechanically with their stored month and amount checked against the
approved evidence, their two leaf dashboards were regenerated, and the
ordinary offline rollup rebuilt the NIH, NSF, and root parents. The focused
retraction test passed and offline NIH validation reconciled all 28 units at
`712003` unique awards. This integration normalization changes no obligation
source, store, baseline, pin, variance, tolerance, residual, or chart
geometry.

The corrected integrated candidate passed the complete fast tier. The unit
suite passed 260 tests with one expected skip, the obligation ledger and all
53 accounts passed, NIH reconciled all 28 units at exactly `712003` unique
awards, and USAspending calibration, the funding-action sentinel, the DMS
baseline, and award invariants across 132 dashboards all passed. The retained
machine-readable result is
`/private/tmp/dod-phase32d-integration-fast.json`.

The rendered tier then passed all four gates using the integrated artifact:
five obligation matrix cases, 212 all-account cases, 59 public-link cases, and
two funding-action sentinel cases. The retained report is
`/private/tmp/dod-phase32d-integration-rendered.json`. The screenshot tier
captured 69/69 reader-review images with no capture failures at
`/private/tmp/dod-phase32d-integration-screens`, with its manifest and
footprint in `/private/tmp/dod-phase32d-integration-screens.json`. Direct
review of the obligations landing page, Defense-Wide account, DHP account,
and sentinel found no clipping, overlap, missing content, or unexpected
warning. Both Stage 3 account charts end at `FY2026P09`; the in-progress year
remains visibly partial while completed years remain pinned. There are no
site-layout or geometry-code changes in the candidate, so no geometry change
requires a before/after exception.

The assembled Pages artifact contains 1,851 files and `337558773` bytes,
leaving `662441227` bytes of headroom below the one-gigabyte Pages limit; its
status is `ok` against the repository's 850 MB warning and 950 MB stop
thresholds. The conservative 52-week trajectory remains flagged because the
short sampled history is dominated by historical backfills, as documented by
the existing footprint model; it is not a release-stop classification.
