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
