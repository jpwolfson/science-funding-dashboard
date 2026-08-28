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
