# Obligation ledger contract

Phase 3.1b adds a second ledger without changing the NSF or NIH award ledger.

| Ledger | Atom | Answers |
|---|---|---|
| Award | one source-native award/application record | How many new awards were made, and how much was committed? |
| Obligation | one File B Program Activity flow, enriched with File C award allocations | How much was obligated from an appropriations account, and when was it reported? |

The ledgers deliberately do not reconcile. Award totals and obligation flows
measure different things.

## Source and completeness contract

Ingestion uses USAspending's official asynchronous custom-account download:

`POST https://api.usaspending.gov/api/v2/download/accounts/`

The obligation ledger has two source layers:

- File B (`object_class_program_activity`) is the canonical account and
  Program Activity dollar series.
- File C (`award_financial`) supplies award, recipient, and transaction detail
  for the award-linked subset of File B.

The adapter resolves the API's internal federal-account ID from the requested
account symbol. Each download selects one account, fiscal year, reporting
period, and submission type. A pull is accepted only when the status reaches
`finished`, the echoed scope matches, ZIP integrity passes, all expected CSVs
and columns exist, the status row count matches parsed CSV records, and every
row belongs to the requested account and year. File C requires Assistance,
Contracts, and Unlinked files.

File B `obligations_incurred` is cumulative through the selected period. The
adapter downloads each available snapshot and derives reporting-period activity
by subtracting the previous snapshot at the account and Program Activity
grain. USAspending performs the object-class and funding-dimension sum in the
download query; subtracting those PA totals is algebraically identical to an
outer-joined full-grain delta. File C
`transaction_obligated_amount` is already reporting-period activity and is
never differenced. Blank File C obligation values are excluded. Signed zero-net
groups with real positive and negative rows remain auditable.

Files A/B/C begin in FY2017 Q2. FY2015 and FY2016 are recorded as unavailable,
FY2017 as partial, and FY2018 as the first full fiscal year. Award-search amounts
must never be used to fill the unavailable years.

## Normalized events and stable identity

Multiple File C rows can share the approved atom because the source also groups
by object class and DEFC. Those rows are deliberately summed in exact cents at:

`(award identity, federal account, Program Activity identity, submission period)`

Program Activity identity prefers PARK. A canonical registry identity may
retain multiple PARK aliases and exact historical code-and-name aliases so the
FY2026 PARK transition and ordinary agency renames do not split pages. Because
agencies can also reuse one code for different named activities, PARK and exact
code/name matches take precedence over an unqualified code; an ambiguous code
without a registered name or PARK fails closed instead of merging programs.
Award identity prefers USAspending's generated award key, then PIID/parent,
FAIN, URI, and finally a deterministic unlinked token.

For each account, Program Activity, and submission-period bucket, the adapter
adds a residual event equal to:

`File B activity - File C activity`

The residual is first-class and may be positive or negative. It represents
payroll, intramural, and other account activity without a File C allocation.
Therefore `File C + residual = File B` exactly.

Persisted events include a stable ID, source (`file_c` or
`file_b_residual`), submission period, derived fiscal year/period/end date,
account, Program Activity code/name/PARK, signed integer cents, award/recipient
metadata where present, source-row count, and gross positive/negative cents.
Unlinked File C rows retain dollars but never inflate `distinctLinkedAwards`.
Missing Program Activities go to visible code `0000` instead of being dropped.
When File C reports non-zero `0000` activity for a period in which File B has
no unknown-PA bucket, the ledger retains that award-linked overlay and creates
an equal opposite `file_b_residual` event in `0000`. The canonical File B net
for that bucket is therefore exactly zero. A File C bucket for any known PA
that is absent from File B remains a fatal scope/alias error.

Period 2 is the first supported monthly window and can include October and
November. Historical quarterly submissions remain quarterly. The dashboard
uses “reported in submission period” and never invents action-month precision.

## Persistence and corrections

Stores are deterministic `FY####.csv.gz` shards plus a schema-v2 manifest and a
committed `FY####.provenance.json` record. A materialized partition is
replaceable because agency submissions can be corrected. Provenance retains
every accepted request scope, source-status and parsed row counts, raw-archive
SHA-256, normalized event-content fingerprint, a compact added/removed/changed
diff, and the fingerprint of the partition it replaced. No row is silently
omitted from a completed download.

The pre-v2 DOE shards are explicitly marked `legacy-migrated`: their normalized
event and shard hashes are committed, but request/status/archive facts that the
pilot discarded are not reconstructed. The weekly rotation replaces those
markers with fully sourced provenance. Raw source ZIPs are retained as 14-day
GitHub Actions artifacts; one-day account-year artifacts carry normalized
shards and provenance into the atomic reconcile job. Normalized events,
manifests, provenance, hashes, and diffs remain in Git.

Before polling an accepted asynchronous request, the puller writes an exact
schema-v1 resume handoff into the raw-artifact directory. A finished download
replaces that handoff with the source ZIP; a timeout -- or any interruption
other than a source-declared terminal failure, including the job's own
timeout cap killing the process mid-poll -- leaves the handoff in the 14-day
raw artifact.

A GitHub Actions rerun of a failed pull-account-year job resumes
automatically, with no manual step: before pulling, the workflow downloads
the previous attempt's raw artifact (if any) into `_raw_previous`, and
`pull_obligation_account.py` reads a handoff found there (`--resume-from`,
defaulted to `_raw_previous` when it exists) exactly as it would a reviewed
one, validating the echoed request scope (`resume_download`,
`require_echo=True`) before resuming. Each handoff also records the writing
run's ID and head SHA; a handoff from the run's own earlier attempt is
always trusted, but one from any other run is resumed only when its head SHA
and account/fiscal-year scope also match, and a handoff with no recorded run
identity is never trusted across runs. The handoff is tried at most once: a
resumed request the source has since declared failed (or an unrecognized
terminal status), or one whose scope no longer echoes, falls through to a
fresh request rather than aborting the job. This closes the failure mode
where `rerun_failed_jobs` blindly resubmitted a new download from scratch and
typically hit the adapter's 2 h cap again (ed/ies FY2018: 7 identical
failures on 2026-09-07; usda/nifa-research-education FY2019: 2 more on
2026-09-19/20).

Resume is also bounded by age. An accepted request whose acceptance time
(encoded in the source file name: `file_name`, `file_url`, or the status
URL's `?file_name=`) is more than `MAX_AUTO_RESUME_AGE_HOURS` (4 h) old has
already outlived the original 2 h cap plus one resumed window. It is
abandoned for a fresh request, so a single stuck source export cannot pin
every later attempt. Evidence: Phase 3.2e run `35963288599`, where
`hhs/nih-ninds` FY2019's File C request, accepted 07:32 UTC, was still
unfinished at 23:32 after one resume.

A reviewed handoff may still be committed temporarily as
`reference/obligation_download_resumes.json` so a bounded retry across
*separate* workflow runs -- not just the current run's next attempt --
resumes the same accepted request and scope instead of submitting a
duplicate download; that manual path is unaffected by the automatic one.

`data/obligations/refresh_status.json` is a small, separately committed store
file, sibling to the per-account event stores above rather than part of any
one account's own directory: one schema-1 object naming every registered
account's current publication freshness (`fresh` or `stale`, with `staleSince`
and `reason` when stale). See "Refresh, freshness, and publication" below for
its exact schema and how the reconcile job, the validator, and the site each
use it.

## Dashboard contract

Every obligation dashboard has `kind: "obligations"`; missing `kind` continues
to mean `awards`. Obligation dashboards publish:

- signed File B totals by reporting period and fiscal year;
- cumulative FYTD totals at submission-period endpoints;
- File C dollars, residual dollars, and `fileCToNetRatio`, the signed File C/net ratio (account-
  level coverage is a special case; PA ratios may fall outside 0–100%);
- distinct linked awards with activity, using set unions at parents;
- top recipients and positive/negative flows from File C only;
- child Program Activities whose canonical dollars add exactly to the parent.

Distinct linked-award counts are not additive. Dollar rollups are additive.
Negative events and residuals remain visible throughout the UI.

## Snapshot acceptance and not-reported periods

Added in the Phase 3.2d remediation (2026-09-17) after HIGH-5: an empty or
near-empty File B period download was previously accepted at face value, so
the cumulative-through-period value collapsed toward zero and the next
period's delta spiked to recover it — a fabricated multi-billion-dollar
swing that no validator caught because `File C + residual = File B` still
held exactly at that broken grain.

**Acceptance rule (universal, registry-free).** A row count of zero is
always `notReported`. Otherwise, a period whose rows fall below half the
last *reported* period's rows is a candidate dip against that frozen
baseline; looking only at periods that already exist for the fiscal year
(never ones not yet pulled), the dip is `notReported` if a later period
recovers to at least half the baseline (**transient** — `dod/navy-rdte`
FY2025 P11: 1 row against 239, P12 recovers to 243) or if no later period
exists at all yet (**provisional** — the fiscal year may still recover on
a future pull); if later periods exist but none recovers, the dip is a
real restructuring (**sustained**): it is `reported` and becomes the new
baseline itself — `commerce/census-current-surveys` FY2020 settles from
101 rows at P06 to 44 at P07 and stays there, and the fiscal-year total
still reconciles to GTAS exactly. Independently, any non-final period
whose rows fall below a quarter of the fiscal year's final accepted
period's rows is also `notReported` (the final period exempt) — this
backward rule catches a run of periods that each look individually stable
next to their immediate neighbors but are collectively tiny next to the
real year-end total (`commerce/noaa-orf` FY2024: 5–10 rows at P04–P08
against 551 at P12); it does not misfire on a genuinely small account
whose early periods are proportionately smaller, not stub-sized (3 rows
against 8 is 0.375 of the final count and passes). There is no per-agency
parameter anywhere in this rule — see the verification regime's governing
principle. A `notReported` snapshot's bytes and provenance are still kept;
it contributes no derived File B activity and no residual event.
`adapters.obligation_common` implements the whole rule once
(`classify_file_b_periods`) and both the pull adapter and the offline
rebuild/validation path (`account_period_status`, reading
`downloads[].statusRowCount` straight from committed provenance) apply the
identical rule, so an existing store is reclassified without a re-pull.

A `notReported` P12 — or, for a fiscal year the baseline already marks
complete, its final recorded period — is a hard error
(`check_final_period_reported`): the year cannot reconcile to GTAS without
a real endpoint, so the pull and the rebuild both fail closed rather than
publish a broken pin.

**Reporting-span reconciliation.** File C is downloaded once per fiscal
year at the latest requested period, with each row carrying its own
`submission_period`; a `notReported` File B period therefore still has real
File C events under its own period label. Reconciliation runs over the
*reporting span* a reported period closes, not the single period:

- File B activity for a reported period = its cumulative snapshot minus the
  last *reported* snapshot before it (skipping any `notReported` periods in
  between).
- The residual booked at that reported period = that delta minus the sum of
  File C events across the whole span it absorbs (the skipped periods plus
  itself).
- A `notReported` period itself keeps its File C events, but gets no File B
  activity and no residual event.
- `File C + residual = File B` holds exactly per span; the FY-total GTAS
  gate is unchanged (it was always a whole-year identity).

A `notReported` period with no later reported period yet fetched (a
dangling tail on an in-progress pull) is left unreconciled — its File C
dollars are real and retained, but unmatched — until a future pull supplies
the covering reported period. This never produces a fabricated swing: no
residual is invented for it either way.

**Dashboard shape.** Every `reportingPeriods` row carries `status:
"reported" | "notReported"`. A `notReported` row publishes no numeric
activity at all (every metric field is `null`); the next `reported` row
that absorbs one or more `notReported` periods carries `coversPeriods`, the
ordered list of periods (itself last) its delta actually spans. Its metrics
are computed over every event in that span (File C and File B residual,
including any a dollar-transient period still carries under its own label),
so within each fiscal year every reported row equals `cumulative(this) −
cumulative(last reported)`, keeps File C + residual = net, and — when the
year's final row is reported — the reported rows sum to the FY total.
`scripts/validate_obligations.py` checks all three cents-exact on every
published dashboard (issue #88: covering rows once carried only their own
period's events, e.g. `dod/navy-rdte` FY2024 P12 at −$25.05B instead of
+$4.15B). Cumulative
(`fyCumulative`) points at a `notReported` period hold the last reported
value and add `held: true`, except when it is also the fiscal year's final
recorded point (nothing later to hold against yet) — that endpoint is
always its real, if incomplete, computed value, so the cumulative-endpoint
invariant (`fyCumulative` last point == that FY's total) still holds
exactly. A `notReported` point with NO earlier reported point yet in the
same fiscal year (a leading run, e.g. `commerce/noaa-orf` FY2024 P02-P11
before P12) instead carries `held: true` with `netObligationsCents: null`
(and null for every other cents/count field) — see "No-prior-reported
display" below.

**Display.** The obligations-by-period chart omits `notReported` rows
entirely — there is no derived activity to plot, so it is neither a zero
nor a gap-worthy point. The cumulative step chart draws a hollow marker
(with a "not reported at pull" title/aria hint) at a held point instead of
the usual filled one. Both charts' tables render the literal text "not
reported at pull" for that row, and the covering row's period label notes
its span, e.g. "P12 (covers P11-P12)".

**No-prior-reported display (Phase 3.2d remediation W14, 2026-09-21).** A
`notReported` point whose fiscal year has no earlier *reported* point to
hold at cannot be shown at its last-reported value (there is none) or at
its own raw through-period sum (a File-C-only partial total that reads as
a real, if small, cumulative). Before this fix, `commerce/noaa-orf`
FY2024 P02-P11 (all `notReported` by the row-count rule) rendered as a
flat $0 line for eleven months before jumping to the real $7.25B at P12 —
indistinguishable from "nothing obligated until September." The fix:
such a point publishes `held: true` with `netObligationsCents: null` (and
null for the rest of `_metrics`'s fields) instead of a computed value — the
cumulative is genuinely *unknown*, not zero. The site's cumulative chart
skips a null-valued point entirely: no line segment into or out of it, no
marker of either kind; the FY's line starts at its first point that does
carry a real value. The period table row for it is unaffected — it already
read the literal "not reported at pull" text for any `held` row regardless
of whether the held value was real or null. The cumulative-endpoint
invariant is unaffected: a fiscal year's final recorded point is a
`reported` period by construction (a `notReported` final period is either
the ordinary `check_final_period_reported` hard error for a complete year,
or the dangling-tail case already computed at its real, if incomplete,
value, both untouched by this fix), so the endpoint this rule could ever
apply to never exists.

**Dollar-transient rule (rule 4; Phase 3.2d remediation W14, 2026-09-21).**
The row-count rule above is blind to a File B snapshot that returns a FULL
row count but an internally inconsistent cumulative dollar total —
`dod/navy-rdte` FY2024: P10 $25.41B → P11 $54.61B → P12 $29.56B (pin
2,956,285,398,710 cents, reconciling exactly at P12); FY2023: P05 $11.04B →
P06 $33.27B → P07 $18.58B. Both the initial spike (an increase, which the
existing >50% *drop* check never looks for) and the partial retreat back
down (44-46%, just under that check's 50% threshold) individually evade
every prior check, so the $54.61B and $33.27B plateaus rendered as genuine
mid-year balances that later "collapsed."

`adapters.obligation_common.apply_dollar_transient_rule` runs after the row
rule, over its `reported` periods only: an interior period (never the
fiscal year's own final period, and only one with both an earlier and a
later `reported` neighbor) is reclassified `notReported` when its
cumulative net obligations differ from the immediately preceding reported
period's cumulative by more than 50% (either direction, using the larger
magnitude as the percentage base so the same formula serves both the
"differs by" and "reverts to" halves) **and** the next reported period's
cumulative reverts back within 50% of that same preceding cumulative. A
deviation that does not revert — a real, sustained change, e.g.
`commerce/nist-its` FY2025 P10 $5.73B → P11 $0.70B → P12 $0.72B (a
confirmed real deobligation) or `dhs/cisa-rd` FY2023 P03→P04 (settles and
stays) — is left `reported` and keeps triggering the existing >50%
cumulative-drop check, which still requires a curated `periodNotes`
explanation. The rule is skipped when the preceding reported cumulative's
magnitude is below the same $1,000,000 floor as the drop check.
`classify_file_b_periods(row_counts, cumulative_cents)` applies both rules
in one call; `account_period_status` (the rebuild/validation path) derives
`cumulative_cents` straight from committed events — summing every event
with `fiscalPeriod` at or before a period's own number telescopes to the
exact true cumulative regardless of any period's own classification, since
a `notReported` period's dollars are always folded into whichever later
reported period absorbs its span, never dropped. The reclassified period
is then treated exactly like a row-rule `notReported` period by the span
reconciliation above: no independent File B activity or residual, its File
C events kept under their own period label, and the next reported row
covers the span. `scripts/rollup_obligations.py` prints the account-years
each rebuild reclassifies this way. The 2026-09-21 offline rebuild
reclassified nine account-years beyond the two DoD examples above: six
Commerce accounts (`commerce/noaa-orf`, `noaa-pac`, `nist-strs`,
`nist-its`, `census-current-surveys`, `census-periodic-censuses`) all at
the identical `FY2023P08` — an apparent single, correlated USAspending
File B submission anomaly across the whole Commerce account family, not
six independent coincidences — plus `usda/nass` `FY2026P04`, confirming
the rule generalizes past the account-years it was designed against
rather than being tuned to them.

`classify_file_b_periods`'s `cumulative_cents` parameter and
`apply_dollar_transient_rule` are wired into the offline rebuild/validation
path (`account_period_status`) as of this addition. The pull path
(`scripts/pull_obligation_account.py`) shares the identical
`classify_file_b_periods` call and already computes each period's raw File
B cumulative in `snapshots` before classifying; passing that cumulative
through is a small follow-up to that file, outside this change's scope.

**`periodNotes`.** A reported-to-reported cumulative File B drop of more
than 50%, where the previous cumulative is at least $1,000,000 (a lower
floor fires on noise — `usda/nifa-integrated-activities` FY2022 P03 fell
from a $24k base), is exactly the shape of the HIGH-5 defect, but real
large deobligations do happen, and a collapsed-dollar/stable-row-count
snapshot (`commerce/nist-its` FY2025 P11, `dhs/cisa-rd` FY2023 P04 — full
row counts, no row rule can classify either one) can be exactly as real or
exactly as broken. `scripts/validate_obligations.py` fails on such a drop
unless that fiscal year's **baseline** file carries a matching entry in
`fiscalYears.<FY>.periodNotes`: a list of `{"period": <int 2-12>, "note":
"<non-empty string>"}`. This is a curated field in the hand-maintained
baseline, never in generated provenance — provenance is byte-regenerated
from the source on every pull and a note living there would vanish (or
silently stay stale) on the next re-pull. A `periodNotes` entry that only
says a CI re-pull is pending, until it lands, is still a legitimate note —
it documents the account's status, not a final explanation.

Each `periodNotes` entry may also carry an optional `publicNote`
(non-empty string, `adapters.obligation_common.baseline_period_notes_problems`
validates it). Unlike `note` — internal curator text (run ids, exact cents,
which re-pull confirmed it) that is never shown to readers — `publicNote`
is a reader-facing statement of what the source itself reported for that
period, written with no cause attribution (no "this was a defect" / "this
was a real deobligation" framing; owner decision 2026-09-21). When present,
`scripts/rollup_obligations.py` copies it into that account's
`dashboard.json` as `periodNotes: [{"fy", "period", "note": <publicNote
text>}]`, sorted by fy then period, and omits the key entirely when no
entry in that account's baseline carries one. This is account-level only —
it does not propagate to Program Activity, agency, or root rollups. The
site renders it, when present, as a "Notes on source figures" block
directly below the fiscal-year period table / cumulative chart on that
account's page (`site/index.html`'s `renderPeriodNotes`).

A `periodNotes` entry need not answer a drop-check finding. A
fiscal-year-level source-figure statement is anchored at that year's final
period (12). The first such entry is the owner-approved caption on
`dhs/cisa-rd` FY2025 (Stage 2 item 8, 2026-09-23). The period chart marks
a noted period with a "see note" guide (Stage 2 item 5).

**Baseline-pin advancement.** A partial fiscal year's baseline pin
(`asOfPeriod`, `obligationsCents`) may only advance onto a period File B
classifies `reported` — a `notReported` period never becomes the pin's
`asOfPeriod`, and the pin keeps its last accepted values instead
(`scripts/pull_obligation_account.py`'s `_baseline_pin`). This closes a
variant of the same defect found in production on 2026-09-17: a scheduled
reconcile run advanced ed/ies's FY2026 pin to `{"asOfPeriod": 10,
"obligationsCents": 0}` from an empty P10 File B snapshot. As a backstop
for a collapse the row-count rule did not already catch, both
`_baseline_pin` and the reconcile-stage `_reject_zero_collapse_pin` refuse
to publish a File A/File B pin of exactly zero cents over a previously
positive pin in the same fiscal year; the last accepted pin is kept
unchanged rather than advanced.

**Validating a not-reported latest period (Phase 3.2d remediation W10,
2026-09-18).** The first full 53-account weekly refresh (run 35253300879)
pulled doe/sc and doe/fossil-energy FY2026 through P10 and, correctly per
the acceptance rule above, classified P10 `notReported` on both (a
provisional dip with no later period yet to test recovery against — 92 of
219 File B rows at doe/fossil-energy, 39 of 149 at doe/sc). The pin
correctly stayed at P09 on both, exactly as designed. Two
`scripts/validate_obligations.py` checks had not been updated for that
otherwise-correct state and failed closed on it: the same-period GTAS pin
check compared the pin's `asOfPeriod` against the latest *stored* period
(P10, which still carries real File C events even though it is
`notReported`) rather than the latest *reported* period (P09); and the
one-residual-per-bucket check expected every `(period, programActivity)`
bucket with a File C event to also carry exactly one residual, which a
`notReported` period never has by design. The fix: for a partial fiscal
year, the same-period pin comparison uses the latest period File B
classifies `reported`, and only once every later period the store actually
holds is itself `notReported` (never a period simply not yet pulled) — a
pin sitting on a `notReported` period, or lagging behind a fully reported
latest period, still fails exactly as before. The residual check skips (as
opposed to zero-asserts) a `notReported` bucket, since an *internal*
mid-year dip that a later pull already covers may still carry a residual
booked under an earlier pull's per-period reconciliation from before that
period was reclassified by a later refinement of the row-count rule — only
the account's own actual dangling latest period is guaranteed residual-free
by construction, and that is what the pin check above depends on.

## Reconciliation gate

For every covered account-year:

Ordinary source rows require:

`sum(File B activity cents) = pinned GTAS/File A obligated cents`

When the official source itself publishes a documented File A/File B warning,
the baseline may instead carry both exact pins and their exact non-zero
variance:

`sum(File B activity cents) = fileBObligationsCents`

`obligationsCents - fileBObligationsCents = fileAFileBVarianceCents`

The published ledger remains File B. The variance is source metadata, never a
synthetic obligation event or a numeric tolerance. All three exceptional
fields are required together, including a non-empty source reason; ordinary
rows continue to fail on a one-cent difference.

and, for every account/Program Activity/reporting-period bucket:

`sum(File C cents) + residual cents = File B activity cents`

The machine-readable baseline is under `reference/`. Missing sources,
unavailable-year misrepresentation, incomplete account/Program Activity
partitions, warnings, or a difference outside an explicitly documented
provisional-period tolerance fail CI. Completed snapshots reconcile to exact
cents. USAspending calibration cannot become `ready` until the full DOE run,
offline invariants, site smoke test, and browser release bar are green.

## Refresh, freshness, and publication

The account registry owns each account's baseline path and source-availability
contract. The scheduled workflow plans an account × fiscal-year matrix from
that registry: every account refreshes the newest source-available fiscal year
weekly and reconciles one historical fiscal year on a rotating basis. A full or
bounded custom plan remains dispatchable.

No single account-year job blocks reconciliation for every other account
(Phase 3.2d remediation W12, "per-account atomicity"). The reconcile job
applies every successfully-staged replacement to one candidate tree, updates
partial baseline pins, rebuilds all manifests and dashboards, validates every
registered account, and runs the rendered browser matrix. Only that exact
validated tree is committed and uploaded as the Pages artifact. The ordinary
award deployment workflow does not independently redeploy obligation-only
commits.

**Per-account atomicity and published staleness.** The reconcile job compares
the planned account × fiscal-year matrix against the partitions this run
actually produced. A missing partition -- current-FY or rotating-historical,
full, or custom -- loses no data: the store's already-committed partition for
that account-year is untouched, so the reconcile job tolerates it. It logs the
skip in the job summary and, for a missing **current-FY** partition
specifically, records the account as `stale` in the committed
`data/obligations/refresh_status.json` (schema 1:
`{generatedAt, accounts: {"<path>": {lastRefreshAttemptAt, lastAcceptedAt,
status: "fresh"|"stale", staleSince?, reason?}}}`), derived from the plan, the
partitions this run actually staged, and each account's latest committed
current-FY provenance `acceptedAt`. An account with a present, accepted
current-FY partition is `fresh`. `staleSince` is the date the account's last
accepted current-FY snapshot was published, and it is preserved unchanged
across repeated failed runs rather than reset to "today" every week -- it
names when the account stopped being current, not when a given run happened
to notice. Reconciliation then proceeds to publish every other account's
refresh regardless; the weekly rotation retries the missing account-year on
its next turn. This distinction, not the pull-job dependency, is what makes
one transient failure in a 100+-job serial matrix no longer discard the whole
weekly pass.

`scripts/validate_obligations.py --check-freshness` and
`--require-current-provenance` read `refresh_status.json` for the same
per-account tolerance: an account beyond the freshness SLA is an error only
if it is not properly marked `stale` with a non-empty `reason`; a marked-stale
account passes freshness, but its `dashboard.json` must still carry the exact
`refreshStatus` object the site renders from (`scripts/rollup_obligations.py`
copies it verbatim into the account's `freshness` block, the obligations root
and agency listing rows, and the root's `staleAccountCount`) -- a dashboard
whose `refreshStatus` disagrees with `refresh_status.json` fails validation, so
staleness can never go undisclosed on a published page. An account beyond the
SLA with **no** entry in `refresh_status.json` at all is still an error:
nothing may go stale silently. The only remaining hard failure at the
reconcile stage is every planned account-year coming up missing at once (an
empty staging directory, or a total plan-vs-staging mismatch) -- a broken run
must never publish a snapshot in which every account is silently marked
stale.

The site renders a stale account's own page with a neutral header note ("Not
refreshed since \<date\>: the most recent scheduled pull for this account did
not complete; figures are the last accepted snapshot.") and marks its row on
every listing table (the account's own agency page, and an aggregated marker
on that agency's row on the obligations root landing page) with a `†` and a
footnote -- the same field-driven pattern `interpretationNote` already uses,
never an agency name check. The underlying figures are still the last fully
validated, accepted snapshot; staleness is a publication-freshness disclosure,
not a data-quality warning.

Publication deliberately separates runtime data from durable audit evidence.
`scripts/assemble_pages_site.py` publishes the site shell and every JSON file
used by the browser, including provenance and event manifests, but excludes
`data/obligations/**/events/*.csv.gz`. Those normalized event shards remain in
Git and continue to drive validation and deterministic rebuilds; the browser
has never requested them. This avoids duplicating hundreds of megabytes of
audit-only archives into GitHub Pages without changing any page, chart, drill-
down, manifest, or provenance behavior.

Every Pages-producing workflow measures the assembled artifact with
`scripts/check_pages_footprint.py`: 850 MB emits a warning and 950 MB blocks
upload, preserving 50 MB below the 1 GB Pages ceiling. If runtime JSON itself
reaches the warning threshold, the next architecture is content-addressed
object storage behind a CDN: upload immutable detail JSON first, publish its
small manifest atomically, and keep aggregate dashboards plus that manifest in
Git. That migration retains page behavior but is intentionally deferred until
the in-repository, runtime-only artifact approaches the warning threshold and
requires a separate owner escalation before any external storage is adopted.
This guard changes only the Pages artifact; Git repository and clone growth
remain reported footprint metrics rather than being redesigned here.

The default freshness SLA is ten days. Production publication fails if the
newest required partition lacks accepted schema-v2 provenance, if its source
acceptance time exceeds the SLA, or if dashboard freshness metadata does not
match the store manifest. Source-unavailable years remain explicit baseline
statuses and are never synthesized.

Official references:

- [Custom Account Data](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/accounts.md)
- [Download Status](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/download/status.md)
- [USAspending sign transformation notes](https://github.com/fedspendingtransparency/usaspending-api/blob/master/data_reformatting.md)
- [USAspending About the Data](https://www.usaspending.gov/data/about-the-data-download.pdf)
