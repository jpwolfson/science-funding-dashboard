# Phase 3.2d execution protocol — coordinating agent

Owner-approved 2026-08-12. This protocol is addressed to ONE coordinating
agent, launched in goal mode with an instruction like **"complete phase
3.2d."** The coordinator orchestrates all worker subagents itself, owns
every merge, and is the only writer to main. It supersedes the sequential
execution rule in `docs/phase-3.2d-agency-roadmap.md` (implementation may
run in parallel under the contracts below) — that document remains the
authority on WHAT each batch onboards; this one governs HOW the work runs.

Scope amendment (owner decision 2026-08-12): NSF obligation accounts ARE
in scope for 3.2d, in wave 1 — the AAAS row-for-row goal requires them,
and onboarding them closes the sentinel's stated NSF coverage asymmetry
(sourced NSF events currently have no financial-ledger counterpart). The
agency-roadmap note descoping NSF/NIH obligation overlays is superseded
for NSF; NIH obligation accounts remain out of scope for 3.2d.

## Roles

- **Coordinator (you):** plans waves, launches and briefs workers, manages
  API concurrency, handles escalations, merges serially, runs cross-cutting
  gates, updates CLAUDE.md exactly once at the end, and brings the owner
  only the escalations listed at the bottom. You never implement an agency
  yourself and you never let a worker merge.
- **Workers (subagents you launch, one per agency batch):** implement one
  agency batch from `docs/phase-3.2d-agency-roadmap.md` on their own
  branch, to the release bar below, ending in an OPEN pull request.

## Wave plan

Run waves in order; within a wave, workers run in parallel subject to the
backfill concurrency cap.

1. **Wave 1:** DOE expansion (roadmap 3.2d-1A then 1B, one worker) and NSF
   obligation accounts (one worker; resolved crosswalk rows only; NSF
   award dashboards are untouched regression fixtures).
2. **Wave 2:** the civilian tail, one worker per roadmap batch — NASA;
   NOAA/Commerce; earth/environment/agriculture; remaining resolved
   civilian accounts (EPA, VA, DHS, NIST, USGS, USDA as the crosswalk
   supports). Widest parallelism lives here.
3. **Wave 3:** DOD, one worker, ALONE — after every other merge is green.
   Its low File C attribution and classified-work disclosures are
   sentinel-adjacent public language: reader review plus owner sign-off
   before merge, no exceptions.

Only crosswalk rows marked `resolved` may be onboarded. `provisional` and
`unresolved` rows are skipped and listed in the final report; they never
block a wave.

## Worker brief (issue verbatim, filling <agency batch>)

> Onboard <agency batch> per `docs/phase-3.2d-agency-roadmap.md`, on a new
> branch `agent/3-2d-<slug>` cut from current main. Read `CLAUDE.md` and
> `docs/obligation-ledger.md` first; follow the working regime.
>
> FILE-OWNERSHIP CONTRACT — you may create or modify ONLY:
> - `data/obligations/<your agency>/**`
> - your accounts' baseline files under `reference/`
> - APPEND-ONLY entries in `config/obligation_accounts.json` and the
>   Program Activity alias tables
> - `docs/phase-3.2d-<slug>-handoff.md` (new file)
> - `tests/test_obligations_<slug>.py` (new file)
> FORBIDDEN: `CLAUDE.md`, `site/**`, shared adapters, shared validators,
> shared workflows, the sentinel, and every other agency's files. If you
> need a shared-code change, STOP that thread of work and report the need
> to the coordinator with a minimal reproduction — do not patch it on
> your branch, even trivially.
>
> RELEASE BAR (all on your branch): registry entries with per-account
> checks; pinned GTAS/File A baselines per account-year; full CI backfill
> green via the branch trigger-file mechanism; exact-cents reconciliation
> (`File C + residual = File B` per PA-period; File B sums = pinned GTAS)
> with documented partial-period pins where sources begin mid-history;
> zero warnings; your own rendered-browser QA on your new account and PA
> pages, light and dark. Deliverable: an OPEN pull request whose body
> carries the evidence. Do not merge. Do not edit the PR after opening it
> except in response to the coordinator.

## Coordinator loop

1. Launch the wave's workers. Cap concurrent CI backfills at 3 across all
   branches (USAspending's download queue is shared); stagger kickoffs
   and hold a worker's backfill start rather than queueing a fourth.
2. On a shared-code escalation: implement the fix yourself on main (or a
   short-lived PR), with tests; all workers rebase before continuing.
   One shared fix on main beats N divergent branch patches — this rule is
   the single most important thing you enforce.
3. As worker PRs open, MERGE SERIALLY, one at a time: rebase onto current
   main; resolve registry/alias appends; run the full offline validator
   suite plus the rendered obligation matrix; merge on green; confirm the
   deploy. Never merge two PRs without revalidating between them.
4. After each merge, spot-check the live obligations landing table — row
   count, ordering, no rendering regressions as the agency list grows.

## Cross-cutting gates before declaring the goal complete

- **Sentinel coverage banner** reflects every newly covered account
  (registry-derived; validation should catch this — verify anyway), and
  the NSF coverage-asymmetry disclosure is retired once NSF accounts are
  live, replaced by actual financial-observation coverage.
- **Site-wide reader review** (working-regime item 5): a fresh
  no-build-context reviewer over screenshots of the grown site — the
  obligations landing page, one account page per agency, one PA page, and
  the sentinel page. Findings gate completion.
- **Footprint check:** report total repo and gzipped-store growth; flag
  (do not fix) if the trajectory threatens Pages' 1 GB ceiling within a
  year of weekly refreshes.
- **Weekly-pipeline soak:** at least one scheduled obligation refresh
  completes green with the full grown registry before the goal closes.
- **CLAUDE.md updated once:** 3.2d checked off with a terse summary and a
  pointer to a new `docs/phase-history.md` entry; per-wave detail goes in
  the history file, not the roadmap.

## Owner escalations (bring as short option memos with a recommendation)

1. DOD disclosure language before the wave-3 merge (standing sentinel
   sign-off norm).
2. Any crosswalk row whose onboarding would change what a published
   number means (measure semantics).
3. Any new external dependency or recurring cost.
4. Nothing else — engineering and build decisions are yours.

## Done means

Every resolved crosswalk account for the roadmap's agencies is live with
exact reconciliation and zero warnings; unresolved/provisional rows are
reported; all gates above are green; the weekly pipeline has soaked; the
owner has the wave-3 memo outcome recorded; CLAUDE.md and phase history
are updated. Report completion with per-agency counts, dollars, and the
live URLs.
