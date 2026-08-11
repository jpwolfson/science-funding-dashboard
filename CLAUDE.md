# science-funding-dashboard

Self-updating public dashboards of federal science funding, organized
agency → directorate → division (NSF nomenclature; each agency's own
equivalent tiers). Successor to `jpwolfson/fed-funding-dashboard` (NSF DMS
only), which stays live and untouched until this repo reaches parity for
that division.

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

- [x] Kickoff: repo created, regime + API lessons documented, DMS pipeline
      and verified baseline seeded under `reference/` (2026-08-07)
- [x] Phase 1 — NSF-wide (completed 2026-08-10):
      - Done: `adapters/common.py` (aggregation regression-verified EXACT
        against fed-funding-dashboard's committed dashboard.json),
        `adapters/nsf.py` (all API-defect workarounds + org-filter probe +
        per-unit plausibility caps from `config/orgs.json` `checks`),
        `scripts/pull_unit.py`, `scripts/rollup.py` (id-deduped rollups,
        child summaries, `data/index.json`), `scripts/verify_dms_baseline.py`
        (exact-parity gate), `scripts/discover_orgs.py`, both workflows,
        `site/index.html` (multi-node port of the old page).
      - **RELEASE BAR MET 2026-08-08 00:02 UTC**: run 31224153926 pull +
        rollup + verify-dms ALL GREEN — fresh full pull = 11,508 awards,
        0 warnings, exact parity with the hand-verified baseline. Owner
        has enabled Pages (Settings done); deploy fires on merge to main.
      - Discovery: run 1 (showAward HTML parser) failed → run 2 (bulk XML,
        commit 93779a9) failed because NSF redesigned Award Search: the
        legacy download endpoint serves a 128-byte meta-refresh stub to
        non-browser clients, and bulk files converted XML→JSON 2025-01.
        v3 proved the ENTIRE legacy /awardsearch/ path — download.jsp
        included, browser UA or not — serves only a 128-byte redirect
        stub; bulk zips remain unreachable. v4 SUCCEEDED via detail-API
        fallback (44 divisions) but review found 3 defects: 16 unresolved
        codes incl. all of TIP (value-pattern extraction missed names
        without a "Division of" prefix), ENG grouped under CSE / AST
        under OD (tie-break bug in name matcher), active=False everywhere
        (recent-window probes inexplicably empty). KEY FACT from v4's
        committed dump: api.nsf.gov/services/v1/awards/{id}.json returns
        EXPLICIT fields divAbbr, dirAbbr, orgCodeDiv, orgCodeDir,
        orgLongName (directorate), orgLongName2 (division). v5 (commit
        fc41f7c, fired 2026-08-09 ~22:10 UTC) extracts by key, checks
        param semantics via orgCodeDiv == swept code, ships all entries
        active:true (derive real flags from pulled data post-backfill).
        Sweep facts established: 59 live org codes, 461 empty, unknown
        codes return EMPTY.
      - REGISTRY DONE (v5, run committed ccb592a, reviewed 2026-08-09):
        59/59 codes verified, 0 unresolved, param semantics exact via
        orgCodeDiv, TIP + ENG + MPS grouping correct, DMS entry intact.
        14 directorate-tier groups = 8 science + OD + 5 admin (BFA, IRM,
        NCO, NNCO, OCIO — kept for completeness). All entries active:true;
        real flags to be derived from pulled data post-backfill.
      - BACKFILL COMPLETE 2026-08-10 01:35 UTC (run 31340113408): all 59
        pulls green, 0 warnings in every unit, rollup green, verify-dms
        exact-parity green post-re-pull. NSF-wide totals: 138,162 unique
        awards since FY2015 (0 cross-division id dups); FY2024 = 11,687
        awards / $8.0B intended (matches NSF's published annual volume);
        FY2026 to date = 5,308 / $4.0B.
      - Active flags derived from pulled data (scripts/derive_active_flags.py,
        24-month window): 40 active, 19 dormant admin/legacy units with
        last-award notes. Re-run after future backfills.
      - Site verified against real data in-browser (9 pages, 0 console
        errors, children tables exactly match rollup JSON). 3 sparse-unit
        display bugs found and fixed (missing tile row on no-current-FY
        units, mechanism-chart label/axis collision, "1 awards" plural);
        fixes re-verified in-browser.
      - Phase 1 exit: PR to main opened + merged by Claude (owner
        pre-approved); Pages deploy fires from update-data runs on main
        (weekly Mondays 09:13 UTC; dispatchable on demand).
      - Known open items: if bulk-XML discovery also fails, diagnose from
        reference/discover_debug/ dumps (now committed even on failure)
        and re-fire via `.github/triggers/discover.json`. Watch the
        report's "not queryable via the API" section — any bulk code the
        API refuses means awards invisible to our pulls. Site review of a
        node with many children (root/agency) once real multi-division
        data exists. Weekly schedule only activates once merged to main.
- [x] Cumulative FY-to-date overlay charts on every node (completed
      2026-08-10 per `docs/handoff-cumulative-fy-charts.md`): `fyCumulative`
      in `aggregate()`, `cumulativeChart` ×2 leading every node page,
      `scripts/reaggregate.py` (offline re-aggregation path — reusable
      whenever `aggregate()` gains keys). All acceptance checks green via
      independent verification sweep: endpoint invariant exact on 256
      year-series across 62 dashboards, DMS byte-parity with
      fed-funding-dashboard@2c211a0 incl. mid-year points, light+dark
      browser pass, awards.csv untouched. Known inherited behavior: FYs
      with zero awards in the 5-year window are absent from fyCumulative
      (fewer lines), not all-zero series.
- [x] Phase 2 — NIH via RePORTER API (completed 2026-08-11, reviewed by
      Fable + independent Sonnet verification sweep):
      - Implementation: 28 current RePORTER administrative components in the
        registry; `adapters/nih_reporter.py` with per-IC/per-FY pagination,
        opposite-order exact ID-set checks, non-destructive merge,
        source-aware award links/labels, and deterministic fiscal-year gzip
        shards. NIH CI runs serially and the adapter throttles to the
        official one-request-per-second guidance. Intramural (`IM`) records
        and subprojects are excluded to avoid zero-dollar records and
        parent/subproject double counting. Layered fail-closed validation
        (`scripts/validate_nih.py`, `docs/nih-data-validation.md`): offline
        shard/manifest/dedup/range/warning gates in the Test workflow, NIH
        like-for-like Data Book benchmarks (counts and dollars ±2%), and `--live`
        same-source reconciliation gating every NIH data refresh.
      - RELEASE BAR MET: backfill run 31426718058 (28/28 ICs green, merged
        via PR #4); Test green on main incl. offline validation; production
        chain exercised end-to-end on main by run 31448155904 (2026-08-11
        01:23 UTC): incremental pull ×28 → rollup → validate --live (28/28
        exact live reconciliations in 29 s) → data commits → Pages deploy,
        ALL GREEN. 694,443 NIH awards FY2015–present, zero warnings in all
        28 stores; Data Book agreement FY2022 +0.12% / FY2025 −0.16%; root
        = 832,616 awards = NSF 138,173 + NIH 694,443 exactly. Sweep: 15
        tests + 33 subtests green, 58/58 dashboards invariant-exact
        (monthly ≡ FY ≡ total; fyCumulative endpoints exact), browser pass
        7 pages × light+dark with 0 console errors, NIH links →
        reporter.nih.gov. Oct–Nov 2025 award collapse (7 / 154 vs ~800 /
        ~2,000 historically) verified as the real shutdown signal, not a
        pull artifact (Oct-1 date-fallback rows are only 0.9% and October
        is NIH's quietest month).
      - Review hardening follow-ups are complete: live NIH validation checks
        the mechanism partition, and NIH-scale dollar tiles use the site's
        billions formatter rather than rendering values such as "$23314M".
      - Phase 3.1b follow-up (2026-08-11): a corrected mechanism whitelist
        recovered 13,790 intentionally in-scope contract/IAA records. The
        former Data Book comparison accidentally measured that complete
        product against a grants-only benchmark. NIH rows now persist funding
        mechanism and activity code; the validator derives the Data Book's
        non-zero grant/OT subset while retaining the complete 708,233-record
        product universe. A fresh 28-IC full pull and rollup are the release
        gate; legacy shards without structured mechanism detail fail closed.
- [x] Phase 3.1 — USAspending award-search adapter + calibration gate
      (completed at its designed STOP 2026-08-11 via PR #5; reviewed by
      Fable, verdict: correct execution, real blocker, sound diagnosis).
      The calibration-before-onboarding ordering worked exactly as
      intended — DOE was NOT onboarded, and the findings drove the Phase
      3.1b redesign below.
      - **CALIBRATION STOP GATE TRIGGERED 2026-08-10 — DOE NOT ONBOARDED.**
        Core award-search adapter and fail-closed pagination checks are built;
        the Phase 2 NIH mechanism tripwire is also built (and exposed missing
        `RDC` / uppercase `OTHER`, now fixed). DMS FY2024 count coverage is
        99.80%, but NIGMS demonstrates that RePORTER application-year records
        cannot be reconciled to USAspending base awards. More decisively, DOE
        089-0222 FY2024 is $9.282B in authoritative account obligations versus
        $3.397B for new awards/current whole-award totals and $37.342B for an
        account-filtered transaction series. Program Activity award filters
        overlap (660 memberships / 575 distinct awards across eight science
        programs), so program-office rollups double-count. Per the ordered risk
        control below, no DOE registry/data/workflow was added. Evidence and
        owner choices: `docs/usaspending-calibration.md` and
        `reference/usaspending_calibration.json`; CI prevents USAspending
        registry onboarding while status is blocked. Recommended next phase:
        redesign around File C account/PARK allocation events.
- [x] Phase 3.1b — obligation ledger + DOE Office of Science pilot
      (completed 2026-08-11 via PRs #6–#9; post-deploy QA, landing-page
      obligation summaries, and deployed Pages smoke checks passed).
      - Two ledgers remain physically separate and clearly labeled. The award
        ledger answers how many source-native awards/applications were made and
        their reported totals. The obligation ledger answers how signed dollars
        moved through an appropriations account by agency submission period.
      - Canonical dollars are File B Program Activity CPE deltas. File C is the
        award-financial subset used for recipient/flow detail; an explicit
        signed File B-minus-File C residual makes every PA-period and account
        total exact. File C is not substituted for GTAS/File B.
      - FY2015–16 are unavailable, FY2017 begins at P06 and is partial-source
        history, FY2018–25 reconcile to GTAS/File A at exact cents, and FY2026 is
        pinned through P09. Correctable fiscal-year partitions are replaceable;
        negative activity remains negative.
      - DOE `089-0222` is live at the account and Program Activity tiers.
        Calibration is `ready`; the NSF DMS count diagnostic and like-for-like
        NIH Data Book gate remain separate award-ledger checks.
      - Post-deploy QA hardening: baselines now drive partial-year rendering;
        zero-activity PA periods are materialized instead of compressing time;
        unmapped nonblank Program Activities fail closed; manifest, required-
        year, residual-bucket, dashboard-freshness, and child-timeline checks
        are enforced. UI copy distinguishes File C/net from a bounded coverage
        score, scopes every current-FY tile, exposes freshness, names charts for
        assistive technology, improves light-theme contrast, and collapses the
        180-row recipient/flow tail behind current-year summaries. The landing
        page now gives DOE obligations the same summary-tile prominence as
        award activity while stating that the measures are separate and that
        negative sign alone does not establish cancellation.
      - Detailed contract and release evidence:
        `docs/obligation-ledger.md`, `docs/phase-3.1b-handoff.md`.
- [x] Phase 3.2a — platformize before account fan-out (completed 2026-08-11).
      - Registry-driven account × FY planning now supports weekly current-FY
        refreshes for every account, one rotating historical reconciliation per
        account, and full/custom dispatches. Baseline paths, availability, and
        the ten-day freshness SLA are account-owned contracts.
      - Per-FY schema-v2 provenance persists accepted request scopes, status and
        parsed row counts, raw ZIP hashes, normalized content fingerprints,
        compact diffs, and replacement lineage across one-day reconcile
        artifacts. Raw ZIPs retain for 14 days; normalized stores and audit
        records remain in Git. Pre-v2 shards are honestly marked
        `legacy-migrated` until rotation replaces them.
      - Reconciliation validates every registered account and renders one
        candidate snapshot before the same tree is committed and uploaded to
        Pages. Obligation-only commits no longer rely on the generic deploy.
      - The hard dashboard migration removed `fileCCoverage` in favor of only
        `fileCToNetRatio`. All obligation JSON was regenerated at schema v2.
      - Fail-closed checks cover required shards, manifests, provenance,
        freshness, dashboard staleness, PA drift, public links, and a five-case
        Chrome matrix across themes, widths, empty/negative/out-of-range ratio
        states, keyboard focus, and console/network failures.
      - Local release evidence: 64 tests plus all offline validators and the
        rendered matrix pass. Detailed contract: `docs/phase-3.2a-handoff.md`.
- [x] Phase 3.2b — build and review the AAAS-to-federal-account crosswalk
      (completed 2026-08-11 as reference-only research).
      Treat the AAAS R&D Appropriations Dashboard as the scope/framing source,
      not as an unattended production registry. Commit a dated source snapshot
      and a reviewed, possibly many-to-many mapping to federal accounts; CI may
      detect AAAS drift but must not auto-onboard or silently remap an account.
      Preserve AAAS-facing labels while making the federal-account identity and
      any aggregation explicit. Each row must be `resolved`, `provisional`, or
      `unresolved`, with evidence. Resolved rows may proceed without waiting for
      optional review of the others. Federal-account hierarchy is canonical;
      AAAS is an alternate grouping/framing view. Source discovery and mapping
      were completed in a separate worktree without changing the registry,
      production workflows, schemas, or generated dashboard data.
      - The dated snapshot preserves 45 AAAS grouping fields and 237 exact
        labels from the public FY 2026 Power BI model; the reviewed crosswalk
        classifies 185 rows as resolved, 10 as provisional, and 42 as
        unresolved, with row-level evidence and explicit account arrays.
      - Artifacts: `reference/aaas_rd_appropriations_2026-08-11.json`,
        `reference/aaas_federal_account_crosswalk.{json,csv}`, and
        `docs/aaas-federal-account-crosswalk.md`.
      - Phase 3.2a satisfies the technical prerequisite, but the crosswalk
        remains reference-only pending reviewed account onboarding. It does not
        authorize automatic registry onboarding, production remapping, workflow
        changes, or automated drift enforcement.
- [ ] Phase 3.2c — non-blocking funding-action sentinel pilot.
      Implement the signal/status/review contract in
      `docs/funding-action-sentinel.md` as two sequential goal-sized tasks:
      - [x] 3.2c-1 core (completed 2026-08-11): generic financial-signal, sourced-event, episode, and
        optional-review stores; gross-negative/cluster detection; stable ledger
        joins; public unreviewed/confirmed/reviewed/restored states; stale-source
        behavior; validation, site rendering, and tests. The independent weekly
        workflow never gates the award or obligation pipelines. Its first
        committed build contains nine File C observations correlated into eight
        unreviewed episodes; File B residuals are structurally excluded. See
        `docs/phase-3.2c1-handoff.md`.
      - [ ] 3.2c-2 source pilots: NSF's structured termination list and a DOE
        portfolio-action example, including award matching where supported and
        separate announced value, observed deobligation, eliminated future
        value, and restoration fields.
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
      2. NSF and other grant-heavy civilian science accounts;
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
