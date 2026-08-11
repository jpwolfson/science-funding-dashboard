# Phase 3.2c-1 handoff

Status: core implementation complete. Phase 3.2c-2 should add the first
authoritative source adapters without changing the store/evidence boundaries
or making optional review a workflow dependency.

## Delivered core

- `data/sentinel/` keeps financial observations, sourced status events,
  optional review findings, source status, and correlated episodes in separate
  versioned JSON stores. The page-facing dashboard is generated from those
  stores; it is not the store of record.
- Financial detection reads only signed File C events from the obligation
  ledger and retains exact stable ledger-event joins. File B-minus-File C
  residuals are excluded before grouping and fail validation if a signal ever
  references one.
- The committed pilot thresholds are $25 million of gross negative activity
  for an individual event, or $25 million across at least five distinct awards
  in one account × Program Activity × submission-period bucket. Gross positive,
  gross negative, and net activity remain separate, so a net-positive grouped
  event can still surface its negative component.
- A qualifying portfolio bucket becomes one observation rather than one alarm
  per award. Recurring observations correlate within the same fiscal year by
  federal account and Program Activity (or award for an individual signal).
  Cross-year or cross-portfolio correlation requires an explicit sourced-event
  key instead of an amount-only inference.
- Stable observation and episode IDs survive row ordering. Detector output that
  disappears after a corrected ledger snapshot is retained as superseded, and
  changed observations retain prior content hashes.
- Sourced events support termination, suspension, appeal, litigation,
  supersession, restoration, and bounded other events. Announced affected
  value, observed deobligation, eliminated future value, and restored value are
  distinct exact-cent fields.
- Source acceptance replaces only that source's active snapshot. A failed
  attempt records an error while preserving the last accepted hash, timestamp,
  event IDs, and events. The public page exposes current/stale/error status.
- Episode rendering supports `unreviewed-signal`, `source-confirmed-event`,
  `reviewed-finding`, `superseded`, and `restored`. An unreviewed episode shows
  its age as “not overdue” and can remain published indefinitely.
- The page publishes the full automation/coverage limitations and the launch
  maintenance-cost estimates. It repeatedly distinguishes financial signals
  from confirmed cancellations.
- A post-launch coverage correction generates the page's prominent financial-
  account and authoritative-source scope directly from their registries. The
  initial disclosure therefore states that financial detection covers only DOE
  Office of Science account `089-0222`, that no authoritative source adapter is
  registered, and that absence from the page is not evidence of no action.
  Validation fails if this disclosure diverges from either registry.

## First committed output

The initial build from the existing DOE Office of Science File C ledger contains
nine financial observations correlated into eight unreviewed episodes. It has
zero sourced events and zero review findings by design: adding NSF and DOE
examples early would have collapsed Phase 3.2c-2 into this core task.

## Workflow isolation

`.github/workflows/update-sentinel.yml` is an independent weekly downstream
job. It rebuilds, validates, runs the unit/site contracts, renders the sentinel
in Chrome, and commits only `data/sentinel`. Award pulls, obligation pulls,
rollups, their validators, and their deployments have no dependency on this job.
No issue, agent, human review, or finding is required.

GitHub Issues remain an optional future convenience. They are not a record of
truth and are not needed for Phase 3.2c-2 source ingestion.

## Release evidence

- 77 unit and static site-contract tests pass after rebasing onto the signed
  reporting-period line visualization from PR #13.
- Sentinel validation reproduces every active observation from the committed
  File C ledger, verifies exact gross/net components and stable joins, rejects
  residuals, rebuilds episode correlation, and checks the public copy contract.
- The funding-action page passes wide/light and narrow/dark rendered-Chrome
  cases with no JavaScript, network, non-public-link, or responsive-layout
  failures.
- The existing five-case obligation rendered-Chrome matrix still passes after
  the shared page gained the sentinel view.

## Phase 3.2c-2 boundary

Add NSF's structured termination list and one bounded DOE portfolio-action
source using the accepted-source helpers. Each adapter must validate and hash
the raw response before acceptance, use authoritative public HTTPS URLs, retain
last-good records on failure, and populate only fields the source supports.
Award matching must be identifier- or source-backed. Do not infer motive,
legality, or financial equivalence, and do not merge announced value with
observed deobligation or eliminated future value.

The required DOE pilot is the [October 2025 announcement](https://www.energy.gov/articles/energy-department-announces-termination-223-projects-saving-over-75-billion)
covering 321 awards, 223 projects, and approximately $7.56 billion across OCED,
EERE, GDO, MESC, ARPA-E, and FE. Preserve “approximately” as an amount qualifier
and record the announcement as an attributed termination event, not as an
observed deobligation. Appeals, closeout, litigation, deobligation, vacatur,
and restoration are later events with their own dates and sources. A direct
order or agency record is required before publishing a vacatur or restoration;
a different court's citation to litigation is not sufficient. Financial
detection for the six named offices remains Phase 3.2d+ account onboarding and
does not block publication of the sourced portfolio event in 3.2c-2.
