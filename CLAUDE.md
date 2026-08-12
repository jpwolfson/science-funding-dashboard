# science-funding-dashboard

Self-updating public dashboards of federal science funding, organized
agency → directorate → division (NSF nomenclature; each agency's own
equivalent tiers).

**Product disposition (owner decision 2026-08-12).** The DMS-only
predecessor (`jpwolfson/fed-funding-dashboard`) is being absorbed by the
American Mathematical Society, which will maintain it on its
government-relations page — do not retire or modify it here. This repo's
goal is the science-wide analogue: a working prototype built for a
similar institutional handoff to AAAS. Every design choice should favor
maintainability by a receiving institution — static hosting, pipelines
that validate themselves, documented contracts, no bespoke
infrastructure, and public methodology a policy audience can cite.

## Working regime — read first, follow in every session

The owner is on a usage-limited plan where premium-model (Fable) tokens are
the scarce resource; wall-clock time and GitHub Actions minutes are not.

1. **Model routing.** The main thread does architecture, API diagnosis, and
   data-integrity reasoning only. Delegate mechanical breadth — per-division
   verification sweeps, adapter boilerplate, CI log triage, config
   authoring — to subagents running Sonnet (`model: "sonnet"` on the Agent
   tool / workflow `agent()` calls).
2. **Long pulls run on CI, never in-session.** Kick off the workflow run,
   schedule a check-in (`send_later`, ~30 min), and end the turn. Never
   poll, sleep, or run multi-hour pulls in the session itself.
3. **One phase per session.** Start each phase in a fresh session; long
   conversations re-send accumulated context every turn. Before ending a
   phase, update the Status section below so the next session can start
   cold from this file.
4. **Data integrity rules** (each one bought with a real bug in the DMS
   project):
   - Never trust a single API query to be complete; union results at every
     level of partitioning. An ineffective partition may only waste
     requests, never lose records.
   - Never delete stored awards on a re-pull. Retain and warn.
   - Verify against independent baselines; per-unit counts may only grow.
     A zero-warning run is the release bar.
   - When counts come up short in a systematic pattern, treat the pattern
     as diagnostic (exactly-one-short-per-window ⇒ pagination offset bug).
5. **Reader review — part of every phase release bar.** Distinct from the
   mechanical browser matrix (which verifies rendering, not
   communication): before release, a reviewer with NO build context — a
   fresh agent given only rendered page screenshots, or the owner —
   answers in writing: What would a first-time visitor conclude from each
   page? What is the most misleading possible reading? Does any label,
   chart form, or juxtaposition imply more than the data supports?
   Findings gate release like any other check. Rationale: every human
   steer to date (sentinel coverage disclosure, obligation chart form,
   presentation logic) has been of exactly this kind — mechanical QA
   passed while a human-obvious reading problem shipped.
6. **Decision layers.** The owner operates at the product/editorial
   layer; agents own engineering and build decisions outright — do not
   ask permission for implementation choices, and do not relitigate
   decisions recorded in this file. Escalate to the owner ONLY:
   (a) measure semantics and editorial framing — what a published number
   or label claims to be; (b) public-claim risk — anything a reader
   could cite as an accusation or conclusion, sentinel language
   especially (owner sign-off is the standing norm for sentinel-facing
   language, per the PR #15 precedent); (c) scope changes, recurring
   spend, or new external dependencies; (d) irreversible data or
   published-history changes. Escalations arrive as short option memos
   with a recommendation, never as open-ended questions.

## NSF Award Search API defects (empirically confirmed 2026-08)

Encode all of these in any adapter touching `api.nsf.gov/services/v1/awards`:

- **`offset` is 0-based** despite documentation suggesting 1-based.
  Paginating from offset=1 silently skips each query's first record.
- **Cross-page duplicate displacement:** queries spanning many pages return
  duplicate records, each silently displacing a record that is never
  returned. Keep result sets ≤ ~60 (`SAFE_WINDOW`) by recursive date
  bisection; partition heavy single days by `transType`, then
  `awardeeStateCode`.
- **Date-filter off-by-one:** unpadded month windows each returned exactly
  one award short. Pad ±1 day and attribute records by their own `date`
  field. The filter may also not operate on the returned `date` field —
  query a wider horizon than the series and attribute by record date.
- **Undocumented params silently ignored:** partition only by documented
  parameters; union everything so an ignored filter cannot lose data.

The working implementation of all of this is `reference/pull_nsf_dms.py`
(verbatim from fed-funding-dashboard), verified exact against a hand-tallied
baseline (`reference/verified_baseline.json`, 11,508 awards, 143/143 months).

## Target architecture

- `config/orgs.json` — registry of org units: agency → directorate →
  division, each leaf carrying its source adapter name + params (e.g.
  NSF `org_code_div`, NIH IC code, USAspending sub-agency/office codes)
  and display names.
- `adapters/` — one module per source: `nsf.py` (generalize
  `reference/pull_nsf_dms.py`), `nih_reporter.py` (Phase 2),
  `usaspending.py` (Phase 3, also the cross-validation source).
- `data/<agency>/<directorate>/<division>/` — per-leaf store +
  `dashboard.json`; NSF uses `awards.csv`, while high-volume NIH uses
  deterministic `awards/FY####.csv.gz` shards plus a manifest. Rollup
  `dashboard.json` at directorate, agency, and root levels. Aggregates
  stay small; the site reads only JSON.
- `site/` — static, one page template reading a node's `dashboard.json`,
  nav from a generated `index.json`. Deployed via GitHub Pages
  (owner enables once: Settings → Pages → Source "GitHub Actions").
- CI — weekly incremental matrix (one job per agency or directorate, each
  committing only its own data subtree; the rebase `-X theirs` retry push
  from fed-funding-dashboard is already concurrency-safe). Full
  reconciliation rotates across units rather than running everywhere at
  once; Actions jobs cap at 6 h.
- Validation — every unit cross-checked against USAspending within
  tolerance; invariant failures and divergences auto-file a GitHub issue
  rather than publishing silently.

## Environment constraint (discovered 2026-08-07)

The remote dev environment has NO egress to api.nsf.gov / www.nsf.gov
(proxy policy 403). Every API-touching task — pulls, probes, org
discovery — must run on GitHub Actions, which has full egress. Two
consequences already encoded:

- `scripts/discover_orgs.py` + `.github/workflows/discover-orgs.yml` do the
  empirical org-registry discovery/verification on CI and commit
  `config/orgs.json` + `reference/org_registry_report.md` back.
- `workflow_dispatch` may be unreliable on non-default branches, so both
  workflows also fire on pushes to `claude/**` that touch their trigger
  file (`.github/triggers/update.json` / `discover.json`); the trigger
  file's JSON fields mirror the dispatch inputs. On `main`, use normal
  dispatch/schedule.

## Roadmap / status

Full completed-phase history, evidence, and discovery narratives live in
`docs/phase-history.md`; summaries here are deliberately terse.

- [x] Kickoff (2026-08-07): repo, regime, API lessons, verified DMS
      pipeline + baseline seeded under `reference/`.
- [x] Phase 1 — NSF-wide (2026-08-10): 59 divisions / 14 directorate
      groups from an empirically verified org registry; full backfill,
      zero warnings; exact DMS-parity gate; multi-node site; weekly CI.
- [x] Cumulative FY-to-date overlay charts (2026-08-10): `fyCumulative`
      on every award node; endpoint-equals-FY-row invariant is the
      acceptance test; `scripts/reaggregate.py` regenerates offline.
      2026-08-12 fix: the partial FY now ends at the latest data date —
      post-dated NIH notice dates had broken the invariant by one award.
- [x] Phase 2 — NIH via RePORTER (2026-08-11): 28 ICs, opposite-order
      exact pagination, deterministic FY gzip shards, fail-closed
      validation incl. like-for-like NIH Data Book gates and `--live`
      reconciliation. 708,233 awards, zero warnings. Release bar met
      including the post-whitelist-fix 28-IC full re-pull (recovered
      contract/IAA records; figure historical, see phase history).
- [x] Phase 3.1 — USAspending award-search calibration (2026-08-11):
      completed at its designed STOP. Award-filtered account measures
      proven structurally wrong for account flows (36.6% under / 402%
      over on DOE 089-0222); drove the 3.1b redesign. CI blocks
      USAspending onboarding unless calibration is `ready`.
- [x] Phase 3.1b — obligation ledger + DOE SC pilot (2026-08-11):
      File B canonical, File C enrichment, first-class signed residual
      (`File C + residual = File B` exact); GTAS reconciliation exact to
      the cent FY2018–25; two ledgers separate and labeled; calibration
      `ready`. Contract: `docs/obligation-ledger.md`.
- [x] Phase 3.2a — platformization (2026-08-11): registry-driven
      account × FY refresh planning, schema-v2 provenance (hashes,
      diffs, replacement lineage), atomic validate-commit-deploy for
      obligation data. Contract: `docs/phase-3.2a-handoff.md`.
- [x] Phase 3.2b — AAAS crosswalk (2026-08-11, reference-only): dated
      source snapshot + reviewed many-to-many account mapping
      (185 resolved / 10 provisional / 42 unresolved, row-level
      evidence). Does NOT authorize automatic onboarding or remapping.
      `docs/aaas-federal-account-crosswalk.md`.
- [x] Phase 3.2c — non-blocking funding-action sentinel pilot (completed
      2026-08-12 via PR #17, integrated by Fable with two validator
      hardenings from the overseer review: accepted current sources must
      have active events exactly equal to acceptedEventIds with a matching
      recordCount, and the DOE announcement source must retain exactly one
      active event once accepted — a truncated or vanished snapshot now
      fails closed instead of passing silently).
      The signal/status/review contract is
      `docs/funding-action-sentinel.md`, implemented as two tasks:
      - [x] 3.2c-1 core (completed 2026-08-11): generic financial-signal, sourced-event, episode, and
        optional-review stores; gross-negative/cluster detection; stable ledger
        joins; public unreviewed/confirmed/reviewed/restored states; stale-source
        behavior; validation, site rendering, and tests. The independent weekly
        workflow never gates the award or obligation pipelines. Its first
        committed build contains nine File C observations correlated into eight
        unreviewed episodes; File B residuals are structurally excluded. See
        `docs/phase-3.2c1-handoff.md`.
      - [x] 3.2c-2 source pilots (completed 2026-08-11): fail-closed adapters
        fetch, validate, hash, and retain last-good snapshots for NSF's
        structured terminated-awards CSV and DOE's October 2025 portfolio
        announcement. The accepted NSF export has 1,667 identifier-backed
        award records; the DOE event preserves "approximately $7.56 billion,"
        321 awards, 223 projects, and the named OCED, EERE, GDO, MESC, ARPA-E,
        and FE offices without inventing award IDs. Announcement, appeal,
        closeout, litigation, deobligation, and restoration are separate event
        types, and the five amount semantics stay separate. Source failure is
        a publishable error/last-good state. No financial account was added and
        no review was required. Coverage asymmetry is a stated case: NSF
        sourced events have no obligation-ledger financial counterpart until
        Phase 3.2d onboards NSF accounts, and source-only episodes render as
        such. See `docs/phase-3.2c2-handoff.md`.
      Financial observations, source-confirmed status events, and optional
      review findings remain separate. Unreviewed signals are a durable public
      state: no data pull, rollup, validation job, or deploy may wait for a human
      or agent. Review issues and agent-prepared PRs are optional conveniences.
      Publish the limits of automated discovery, motive/legal interpretation,
      award mapping, and announced-value/deobligation comparison, plus
      maintenance-cost estimates at launch. Replace estimates with measured
      figures after eight weeks as a non-blocking operational follow-up; do not
      keep an agent goal open or delay account fan-out while the clock runs.
- [ ] Phase 3.2d+ — fan out in bounded agency batches after
      3.2a/3.2b and the 3.2c launch are green.
      Use one goal-mode task per batch, each adding registry entries, baselines,
      backfill, exact reconciliation, Program Activity aliases, site pages,
      tests, and rendered-browser QA:
      1. DOE expansion, beginning with ARPA-E and applied/clean-energy accounts;
      2. NSF and other grant-heavy civilian science OBLIGATION accounts
         (the NSF/NIH award-ledger dashboards have been complete since
         Phases 1-2; this batch adds their appropriations-account flows);
      3. remaining resolved civilian R&D accounts (NASA Science, NOAA, NIST,
         USGS, USDA, EPA, VA, and DHS as the crosswalk supports);
      4. DOD and classified/intramural-heavy accounts last, with the standard
         disclosure that canonical File B totals remain complete while public
         File C award attribution may be limited.
      - Retain all File C instrument classes (grants, cooperative agreements,
        contracts, IAAs, and unlinked rows) while File B remains canonical.
      - At account level, report the File C portion and residual. At PA level,
        label File C/net as a signed ratio that may be negative or exceed 100%
        when File C and residual activity offset; never call that a completeness
        percentage without qualification.
      - Low File C attribution for classified or intramural work is an award-
        detail limitation, not under-reporting of canonical File B obligations.
      - Gross positive/negative File C activity is retained as a financial fact
        and feeds the separate sentinel without being labeled a cancellation on
        amount or sign alone. Unresolved crosswalk rows and optional sentinel
        review never block ready accounts or unrelated publication.
