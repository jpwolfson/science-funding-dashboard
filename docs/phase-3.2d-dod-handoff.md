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
