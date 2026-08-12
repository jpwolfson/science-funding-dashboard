# Funding-action sentinel and optional review process

Status: Phase 3.2c completed 2026-08-11. The signed obligation ledger supplies
gross-negative File C observations to a separate, versioned sentinel store and
public page. The first authoritative-source adapters ingest NSF's structured
terminated-awards CSV and DOE's October 2025 portfolio announcement. The
sentinel does not classify financial signals as cancellations and does not
maintain a required review queue.

## Purpose

The sentinel is intended to make material reductions, agency-announced
terminations, portfolio actions, and later restorations easier to find and
investigate. It is not intended to decide whether an action is routine,
political, lawful, or ultimately effective.

The operating constraint is firm:

> Data pulls, validation, rollups, and publication must never wait for a human
> or agent review. An unreviewed signal is a valid durable state, not a failed
> workflow or an overdue task.

The site may therefore publish an automatically generated **sentinel signal**.
It must not publish that signal as a confirmed cancellation unless an accepted
authoritative source says that the award or portfolio was terminated or
cancelled. Review can add interpretation and links, but is not required to keep
the dashboard current.

## Three kinds of record

The implementation must keep these concepts separate:

| Record | Meaning | May be produced automatically? |
|---|---|---:|
| Financial observation | A signed File C award flow or other directly reported financial fact | Yes |
| Sourced status event | An agency or court source explicitly reports a termination, suspension, appeal, order, or restoration | Yes, when extraction is deterministic |
| Review finding | A human or agent assesses how a signal and its sources should be understood or linked | Optional |

A negative obligation is a financial observation, not proof of cancellation.
A termination may also eliminate unobligated future funding without producing
an equal negative obligation. Announced affected value, prior obligations,
posted deobligations, eliminated unobligated value, and later restorations must
remain separate fields. Source qualifiers such as “approximately” or “up to”
are part of an amount's meaning and must survive normalization and public
rendering.

File B-minus-File C residual events are reconciliation facts and must never be
used as cancellation candidates.

## Responsibility model

| Responsibility | Default owner | Required for publication? |
|---|---|---:|
| Publish the underlying status or legal action | Agency or court | No; financial signals may exist without one |
| Fetch registered sources, detect signals, retain evidence, and render states | GitHub Actions and repository code | Yes for the sentinel update, but failure must not block unrelated dashboard updates |
| Interpret an ambiguous episode or improve award mapping | Any later human or agent reviewer | No |
| Accept a judgment-sensitive characterization | Repository owner through an ordinary pull request | No |
| Repair a broken source adapter | A maintainer when available | No; the source remains visibly stale meanwhile |

There is deliberately no standing human operator. Repository code owns routine
collection and surfacing; a reviewer owns only the particular finding they
choose to submit. No person or agent owns a queue that must be cleared.

## Automatic pipeline

Phase 3.2c should add a generic funding-action store rather than a
`cancelled=true` field to either existing ledger.

1. **Collect known authoritative sources.** A registry identifies official,
   bounded sources and their extraction rules. Machine-readable sources such
   as an agency CSV are downloaded, schema-validated, hashed, and diffed.
   Known official announcement or case pages may be watched for content
   changes, but a changed page is not automatically interpreted beyond fields
   that can be extracted deterministically.
2. **Generate financial signals.** A detector reads linked File C activity,
   using gross negative activity rather than only a grouped net amount. It
   applies committed materiality and portfolio-cluster rules, deduplicates
   recurring observations into an episode, and excludes File B residuals.
3. **Normalize durable records.** Signals and sourced events are written to a
   committed, versioned store with stable IDs, source URLs and hashes,
   observation dates, award/account links where known, amounts with explicit
   semantics, and review state.
4. **Build the site regardless of review state.** The public sentinel page
   renders `unreviewed signal`, `source-confirmed event`, `reviewed finding`,
   `superseded`, and `restored` as distinct states. It shows source freshness
   and the age of an unreviewed record without calling it overdue. A prominent,
   registry-derived banner names the current financial accounts and registered
   authoritative sources and warns that absence is not evidence that no funding
   action occurred.
5. **Optionally mirror reviewable records.** CI may open or update a GitHub
   Issue for convenience. An issue is not the store of record, and failure to
   create or close one must not block ingestion or deployment.

If a sentinel source is unavailable or changes schema, that source's last good
snapshot remains published with a visible stale/error status. The ordinary
award and obligation pipelines continue. A malformed new source response must
not overwrite the last accepted snapshot.

## What the site should surface

An unreviewed signal should show only mechanically supportable facts:

- the threshold or cluster rule that fired;
- affected award IDs, accounts, programs, and recipients where available;
- gross negative activity, net activity, and reporting period;
- any exactly matched official source;
- source and data freshness;
- an explicit statement that the signal has not been classified as a
  cancellation.

A source-confirmed event may additionally show the agency's event type and
reason as stated, effective date, announced affected value, and affected-award
list. Those are attributed agency statements, not dashboard conclusions.

The primary public unit is an **episode**, which may connect many awards,
financial observations, sourced events, litigation events, and restorations.
This prevents hundreds of related terminations from becoming hundreds of
independent alarms and prevents later reinstatements from erasing the original
history.

### Attributed-language rendering rule (owner-approved 2026-08-12)

Render by provenance, not judgment. Any string whose value comes from an
authoritative-source VERBATIM field — announcement titles and qualified
amount display strings such as "approximately $7.56 billion" — renders on the
sentinel page only through one shared `attributedText()` helper. The helper wraps the string in quotation marks and
shows its citation: the source's registered name and its source-as-of date,
linked to the source URL where the record has one. Several attributed strings
from the same source may render together in one block with a single shared
citation rather than one repeated per line, but every attributed string is
still individually quoted.

Adapter-composed paraphrases are the deliberate exception: a paraphrase in
quotation marks would attribute the dashboard's own wording to the agency,
which is the inverse attribution error. Fields that paraphrase a source
(`statedReason`) render unquoted, explicitly labeled — "Stated reason
(paraphrase, not verbatim): …" — and written so the source is named as the
actor ("DOE attributed the decision to …"). Dashboard meta-commentary never
appears inside quotation marks.

Strings in the dashboard's own voice — card headings, labels, state
descriptions — are composed mechanically from registry or store metadata and
never contain source language. In particular, **agency headlines never occupy
heading positions, even quoted.** A sourced episode's card heading (for
example the DOE portfolio-action announcement or the NSF terminated-awards
list) is composed mechanically from structured fields — the registered
source's ID, the event type, and the event date, e.g. "DOE portfolio-action
announcement — October 2025" — never from the source's own headline text.
That headline instead renders in the card body as a quoted, cited line.
Financial-observation episode headings (program-activity names drawn from the
registry) were already mechanical and are unchanged by this rule.

This is enforced two ways so it cannot regress silently: a contract test
(`tests/test_site_contract.py`) statically checks that the attributed field
names are interpolated only via `attributedText()` calls in `site/index.html`,
and never bound to a heading or a link's text directly; and the rendered
smoke test (`scripts/smoke_sentinel_page.py`) drives a headless browser and
asserts the DOE source headline text appears on the rendered page only inside
quotation marks, and never inside any heading element (h1-h4 — the page has
no separate card-heading class).

## Optional review process

There is no assigned reviewer, review deadline, or minimum review cadence.
Anyone with repository write access may ask an agent to review a record or may
review it directly.

A review should:

1. confirm that cited sources are authentic and actually support the proposed
   event type;
2. distinguish agency statements, challengers' allegations, and court actions;
3. map awards to a portfolio episode only when identifiers or a cited source
   support the mapping;
4. distinguish announced value from observed financial effects;
5. record one of the bounded findings below; and
6. submit the finding as a tested pull request that appends or supersedes
   records rather than silently rewriting history.

Suggested findings are:

- `confirmed-status-event`
- `routine-or-administrative-adjustment`
- `portfolio-action-awards-not-fully-mapped`
- `duplicate-of-episode`
- `insufficient-evidence`
- `superseded-or-restored`

A reviewer must not replace attributed language with an unsupported motive or
legal conclusion. Terms such as “political,” “retaliatory,” “unlawful,” or
“constitutional” belong only in clearly attributed claims or current court
holdings, with dates and sources.

Review is additive. If no review occurs, the signal remains visible with its
original state. If a later source resolves the question deterministically, the
pipeline may append a sourced event without waiting for review.

## What cannot be implemented reliably in code

The repository should state these limitations on the sentinel page as well as
here:

- **Complete discovery.** There is no complete, uniform federal feed of award
  terminations, suspensions, appeals, settlements, and reinstatements. A watcher
  can cover registered sources, not every new page, letter, docket, or
  announcement.
- **Motive.** Transaction amounts and agency prose cannot establish why a
  decision was made beyond the reason attributed to a source.
- **Legal judgment.** Code cannot determine whether an action is lawful,
  whether a preliminary order will survive appeal, or whether a contested
  action is finally effective.
- **Financial equivalence.** An announced “saving” or affected award value is
  not necessarily a posted deobligation. Public data may not reveal how much
  future unobligated funding was eliminated.
- **Award mapping from prose.** A portfolio announcement that omits award IDs
  cannot be completely joined to award-level records without another source.
- **Routine-versus-extraordinary intent.** Amount and clustering rules can
  prioritize unusual activity, but cannot conclusively distinguish normal
  amendments, closeout, corrections, partial reductions, and terminations.
- **Real-time legal monitoring.** Reliable comprehensive docket monitoring may
  require a paid or access-controlled external service. Without one, the
  dashboard can monitor registered public pages and cases but cannot promise
  immediate or complete litigation updates.
- **Independent truth verification.** Archiving a source and reporting what it
  says does not independently prove the source's factual claims.
- **Review itself.** Software can assemble evidence and propose a finding; the
  exercise of judgment remains optional human or agent work.

These are coverage limitations, not reasons to stop ordinary publication.

## Expected burden and cost

The estimates below are planning ranges for an initial sentinel covering NSF,
DOE, and roughly 10–30 obligation accounts. They exclude the existing award and
obligation pulls and should be replaced with measured figures after eight weeks
of operation.

The eight-week measurement is a non-blocking operational follow-up. It is not a
Phase 3.2c launch gate, a prerequisite for account fan-out, or a reason for an
agent goal to remain open while time passes.

| Activity | Initial implementation | Recurring burden |
|---|---:|---:|
| Generic store, detector, validation, workflow, and site view | 3–6 engineering days | Ordinarily none outside failures |
| Each structured agency source | 0.5–2 engineering days | 1–4 engineering hours when its URL or schema changes |
| Each unstructured known-page watcher | 0.5–1.5 engineering days | Occasional repair; extraction must remain deliberately narrow |
| Weekly source fetch, diff, and signal build | Included above | About 10–60 GitHub-hosted runner minutes/month at pilot scale |
| Committed normalized records and changed-source snapshots | Included above | Roughly 1–20 MB/year at pilot scale; raw transient downloads can use short-retention Actions artifacts |
| Straightforward optional agent review | None required | Roughly 10–30 minutes per episode |
| Ambiguous mapping or legal-status review | None required | Roughly 30–120 minutes per episode; may remain unresolved indefinitely |
| Human review | None required | Zero by default; optional spot checks or judgment calls |

At pilot scale the expected direct infrastructure cost is zero beyond the
repository's existing GitHub plan if the work stays within its included Actions
and artifact allowances. That is an operating assumption, not a guarantee of
future GitHub pricing. Broad news discovery, comprehensive court-docket access,
or a continuously running external service would create a new paid dependency
and is explicitly outside the baseline design.

The main practical costs are episodic adapter repair and optional interpretation,
not storage or scheduled computation. Review volume should be measured by
signals generated, episodes deduplicated, optional reviews completed, false or
routine signals identified, and source-adapter failures. If the detector
generates more than about ten new episodes per agency per month, its thresholds
or episode correlation probably need recalibration; that condition should be a
maintenance signal, not a review SLA or publication gate.

## Phase 3.2c acceptance criteria

- No award pull, obligation pull, rollup, validation job, or deployment waits
  for review.
- The durable store and public page support an indefinite unreviewed state.
- No financial observation is labeled a cancellation solely because it is
  negative.
- Structured authoritative events ingest without manual transcription after
  their source adapter is accepted.
- File B residuals cannot trigger signals.
- Gross negative activity remains detectable when the same grouped event has
  larger positive activity.
- Episodes deduplicate portfolio actions and preserve later appeals,
  litigation, supersession, and restoration.
- Source failure preserves the last good record, exposes staleness, and does
  not stop unrelated publication.
- GitHub Issues and agent reviews are optional conveniences, not dependencies.
- The site publishes the limitations above and never implies complete federal
  cancellation coverage.
- The site's current-coverage disclosure is generated from the obligation and
  source registries and fails validation if it becomes stale or is omitted.

## Phase 3.2c-2 source-pilot outcome

The NSF adapter accepts only the official CSV's bounded schema: award ID,
directorate, recipient, title, source-listed obligated amount, and export date.
Its first accepted June 5, 2025 export contains 1,667 unique award identifiers.
The source does not provide award-specific termination dates or reasons, so the
normalized records do not invent them. Source-listed prior obligations remain
separate from announced value and observed deobligation.

The DOE adapter watches only the official October 1, 2025 announcement and
fails closed if its bounded facts drift. The normalized event is an attributed
announcement of termination preserving “approximately $7.56 billion,” 321
awards, 223 projects, and Office of Clean Energy Demonstrations (OCED), Energy
Efficiency and Renewable Energy (EERE), Grid Deployment (GDO), Manufacturing
and Energy Supply Chains (MESC), Advanced Research Projects Agency-Energy
(ARPA-E), and Fossil Energy (FE). The source publishes no award identifiers, so
the adapter makes no award-level match. The announced amount is not populated
as an observed deobligation, eliminated future value, or restoration.

An announcement does not stand in for a later appeal, closeout, litigation,
deobligation, or restoration. Those lifecycle types normalize to separate,
stable sourced-event records with their own dates, sources, and amount
semantics. The sentinel workflow fetches sources before rebuilding, but a
source error retains the last accepted hash and records while publication of
unrelated award and obligation data continues. No financial-account expansion
or manual review was a launch dependency.
