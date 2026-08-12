# Phase 3.2d+ agency fan-out roadmap

Status: execution plan. Phase 3.2d implementation begins after Phase 3.2c-2 is
merged and green. Phase 3.2a supplies the schema-v2 registry/workflow contract;
Phase 3.2b supplies a reviewed reference crosswalk; Phase 3.2c supplies the
separate funding-action sentinel. None of those phases authorizes unattended
account onboarding.

This roadmap expands the short agency list in `CLAUDE.md` into goal-sized
batches. It prioritizes high-value science accounts while keeping mixed-purpose,
many-account, classified, and intramural-heavy portfolios from distorting the
meaning of the dashboard.

NSF and NIH are already complete production agency tracks. They are reference
implementations and regression fixtures for Phase 3.2d, not candidates for
account onboarding or a second obligation-based build. Any future NSF or NIH
obligation overlay would be a separately scoped enhancement, not part of this
roadmap.

## Execution rules for every batch

SUPERSEDED 2026-08-12 (owner-approved): batches now run under the parallel
worker/coordinator protocol in `docs/phase-3.2d-execution-protocol.md` — one
coordinating agent launches parallel per-agency workers under strict
file-ownership contracts and merges serially. The sequential rule below is
retained for context only. The same decision brings NSF obligation accounts
into 3.2d scope (wave 1), superseding this document's NSF descoping note;
NIH obligation accounts remain out of scope.

Original (superseded) rule: use one goal-mode task per implementation batch
and run implementation batches sequentially. Read-only account research may
run in parallel, but registry, workflow, generated-data, and site changes
share enough files that parallel implementation is more likely to create
conflicts than save time.

Each task must start from current `main` and, for every account it attempts:

1. identify the canonical federal-account code and title from an official
   account source, using the Phase 3.2b crosswalk as evidence rather than as an
   import file;
2. pass the USAspending calibration/onboarding gate independently; an account
   that fails is parked with a documented reason and does not block ready
   accounts in the same batch;
3. add the schema-v2 registry entry, baseline, availability boundary, and
   reviewed Program Activity aliases without silently mapping unknown codes;
4. perform the one-time historical backfill and exact File B reconciliation,
   retaining File C grants, cooperative agreements, contracts, IAAs, and
   unlinked rows as signed award-financial detail;
5. use the normal weekly current-FY incremental refresh and rotating historical
   reconciliation after launch; never turn account fan-out into weekly full-
   history repulls;
6. build account, agency, and federal rollups, preserving stable IDs and exact
   cents, and regenerate the sentinel so its public financial-coverage banner
   reflects the newly live accounts automatically;
7. add unit, validation, site-contract, and representative rendered-browser QA
   covering at least the agency root, one account, and any empty, negative, or
   out-of-range signed-ratio state introduced by the batch; and
8. commit a handoff recording account-by-account status, reconciliation totals,
   File C/net scope, unmapped Program Activities, runtime, artifact growth, and
   any account that was deliberately deferred.

Default to one to three accounts per task. A batch may include four or five only
when they share an agency, adapter behavior, and a small enough backfill to stay
within the existing GitHub Actions limits. Raw source downloads remain transient
or short-retention Actions artifacts; only validated normalized/provenance
artifacts belong in Git.

No task waits for a human review queue. Provisional or unresolved crosswalk rows
are skipped or parked while independently resolved accounts continue. Manual
judgment is required only before accepting a disputed mapping, not for ordinary
publication of already validated accounts.

## Presentation rules across agencies

- The federal account is the canonical financial unit. An AAAS label or agency
  program is an alternate grouping and must never be turned into a synthetic
  federal account.
- File B signed obligations are canonical at account level. File C is the
  award-linked gross-flow layer. Low File C attribution does not make File B
  incomplete.
- A mixed-purpose account is displayed under its official account title. Do not
  label the entire account “R&D” merely because AAAS identifies R&D lines within
  it. Show an R&D or mission subset only when a reviewed Program Activity or
  other official dimension supports that subset exactly.
- Program Activities, DoD budget activities, mission directorates, budget line
  items, and program elements are not interchangeable. Crosswalk them only with
  direct evidence and keep the canonical account total visible.
- Gross positive and negative File C activity remains signed. Neither a negative
  transaction nor a large cluster is labeled a cancellation without an accepted
  sourced status event.
- Many-to-many AAAS totals are calculated views across live canonical accounts.
  Onboarding one member must not imply that the total is complete.

## Ordered agency tracks

### 3.2d-1 — DOE expansion

#### 3.2d-1A: clean-energy financial coverage

Onboard the accounts needed to observe the offices named in the October 2025 DOE
portfolio action. Begin with the resolved ARPA-E (`089-0337`), EERE
(`089-0321`), OCED (`089-2297`), Fossil Energy (`089-0213`), Electricity
(`089-0318`), and CESER (`089-2250`) candidates, but calibrate the exact
office-to-account relationship before selecting each batch. GDO and MESC office
labels must not be assumed to equal one federal account merely because the
announcement names the office.

Split this into at least two tasks: ARPA-E/EERE/OCED first, then the remaining
validated clean-energy accounts. Phase 3.2c-2's sourced DOE episode may publish
before these accounts are live; financial observations attach later when exact
ledger evidence exists.

#### 3.2d-1B: remaining resolved DOE research accounts

After the clean-energy batches are stable, evaluate Nuclear Energy (`089-0319`),
NNSA Weapons Activities (`089-0240`), Defense Nuclear Nonproliferation
(`089-0309`), and EIA (`089-0216`) as separate bounded tasks. DOE Office of
Science (`089-0222`) is already the production reference account and is not
re-onboarded.

### 3.2d-2 — NASA

#### 3.2d-2A: NASA Science pilot

Onboard NASA Science (`080-0120`) first. It has the clearest value for this
dashboard and exercises multiple AAAS mission labels—Astrophysics, Earth
Science, Heliophysics, Planetary Science, and Biological and Physical Sciences—
inside one canonical account. Publish those mission views only where Program
Activity evidence supports them; otherwise retain them as crosswalk context.

NASA's heavy use of contracts, cooperative agreements, and interagency activity
makes gross instrument-class retention and the File C residual especially
important.

#### 3.2d-2B: research and engagement missions

Onboard Aeronautics (`080-0126`), Space Technology (`080-0131`), and STEM
Engagement (`080-0128`) as a second task.

#### 3.2d-2C: exploration and operations

Onboard Exploration (`080-0124`) and Space Operations (`080-0115`) last within
NASA. These accounts contain large acquisition, infrastructure, and operational
flows; use official account titles and do not present the full account as
research. “NASA Total” becomes complete only after all six accounts are live.

### 3.2d-3 — NOAA and the Commerce science accounts

#### 3.2d-3A: NOAA

Onboard NOAA Operations, Research and Facilities (`013-1450`) and Procurement,
Acquisition and Construction (`013-1460`) together or in two sequential tasks.
ORF mixes research with operational activity, while PAC includes major capital
and weather-satellite acquisition. The canonical pages therefore use the
official account titles. OAR research and weather-satellite views are allowed
only when reviewed Program Activity mappings support them exactly.

#### 3.2d-3B: NIST

Onboard Scientific and Technical Research and Services (`013-0500`) and
Industrial Technology Services (`013-0525`). Their sum may support an explicit
AAAS “NIST Total” alternate view after both are live.

#### 3.2d-3C: Commerce statistical accounts

Evaluate BEA (`013-1500`) and the Census Current Surveys (`013-0401`) and
Periodic Censuses (`013-0450`) accounts. These are statistical capacity rather
than conventional grant R&D; keep that distinction visible and do not duplicate
accounts already onboarded through another track.

### 3.2d-4 — earth, environment, and agriculture

#### 3.2d-4A: USGS and EPA

Onboard USGS Surveys, Investigations and Research (`014-0804`) and EPA Science
and Technology (`068-0107`). Both have useful Program Activity structure, but
aliases must be reviewed against actual ledger codes rather than copied from
AAAS program labels.

#### 3.2d-4B: USDA research

Split USDA into at least two tasks:

- ARS Salaries and Expenses (`012-1400`) and Buildings and Facilities
  (`012-1401`), plus Forest and Rangeland Research (`012-1104`);
- NIFA Extension (`012-0502`), Research and Education (`012-1500`), and
  Integrated Activities (`012-1502`).

ERS (`012-1701`) and NASS (`012-1801`) belong in the statistical-agency pass if
they have not already been onboarded. ARS and NIFA totals are many-account
alternate views and remain visibly partial until every member is live.

### 3.2d-5 — other civilian research and statistical agencies

Run small, coherent tasks rather than one “miscellaneous” batch:

- VA Medical and Prosthetic Research (`036-0161`);
- DHS Science and Technology (`070-0803`), CISA R&D (`070-0805`), and CWMD R&D
  (`070-0860`);
- DOT Research and Technology (`069-1730`), FAA RE&D (`069-8108`), and Railroad
  R&D (`069-0745`);
- Institute of Education Sciences (`091-1100`);
- AHRQ (`075-1700`) and ASPR/BARDA R&D and Procurement (`075-1000`); and
- the remaining statistical accounts for BLS (`016-0200`), BJS (`015-0401`),
  ERS, NASS, BTS, NCES, NCSES, and EIA, deduplicating any account already live
  through its parent-agency track.

Do not onboard the unresolved CDC-wide aggregate. NCHS and Project BioShield
remain provisional until a separate mapping review resolves their account/time
scope; their deferral does not block AHRQ, BARDA, or other resolved accounts.

### 3.2d-6 — DoD research

DoD remains last because account totals are available while public award-level
attribution and program detail can be structurally limited by classified,
intramural, interagency, and contract-heavy activity.

Use three sequential tasks:

1. Army RDT&E (`021-2040`) and Navy RDT&E (`017-1319`);
2. Air Force RDT&E (`057-3600`) and Space Force RDT&E (`057-3620`); and
3. Defense-Wide RDT&E (`097-0400`) and Defense Health Program (`097-0130`).

The five RDT&E accounts support an explicit service/Defense-Wide aggregate.
AAAS 6.1 basic research, 6.2 applied research, 6.3 advanced technology, and
broader 6.1–6.6 totals are alternate budget-activity concepts. Do not derive
them from File C instrument type, Program Activity name, or account arithmetic.
Add a 6.x view only if an official source and stable ledger dimension support an
exact, tested mapping.

Every DoD page must state that File B account obligations remain canonical even
when recipient/award attribution is sparse. A low File C/net ratio is an
award-detail limitation, not proof of missing account dollars.

## After the agency tracks

Once the new tracks cover the structural families not already exercised by the
complete NSF and NIH implementations—contract-heavy, mixed-purpose,
many-account, and low-attribution—add the AAAS alternate grouping layer and
drift detector as a separate reviewed phase. It may flag changed labels,
account arrays, or model identity, but it must never auto-onboard, delete, or
remap an account.

Measure GitHub Actions runtime, compressed repository growth, sentinel episode
volume, and browser-matrix duration after each batch. If a limit is approached,
reduce batch size or rotate historical reconciliation more slowly; do not
silently weaken exact File B reconciliation, provenance, or signed-flow rules.
