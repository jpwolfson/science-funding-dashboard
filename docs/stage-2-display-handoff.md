# Stage 2 display batch: handoff record

This is the running record for executing `docs/display-improvements-ledger.md`
items 1–11 as one reader-review-gated release. A cold start should read this
file, then `CLAUDE.md`, then the ledger.

## Rules (binding, from the ledger header and the coordinator brief)

- Display only. No data, store, or measure-semantics changes. Nothing that
  smooths, interpolates, or invents precision.
- Integration branch `claude/stage2-display`, cut from `main` at `c356a78`.
  Item clusters are developed on `claude/sweet-heisenberg-7u5lhz` and land
  in the integration branch as PRs. One final PR goes to `main` after the
  reader review passes. Nothing ships piecemeal.
- `site/index.html` is one file, so workers run one item cluster at a time.
- Do not change strings pinned in `tests/test_site_contract.py` without
  owner sign-off. That covers the DoD interpretationNote, the award-root
  coverage line, the obligation subtitle, the sentinel language, both "Not
  refreshed since" notes, the NIH methodology line, and the two publicNotes.
- Do not merge to `main` while an `Update obligation ledger` reconcile may be
  in flight, roughly Mon 10:37 UTC to Tue ~23:00 UTC; its reconcile runs the
  rendered tier against `main`'s tip.
- Evidence per item: fast and rendered tier JSON; before/after card
  screenshots at 1100 px for every chart whose geometry changes
  (`scripts/capture_cards.py`); contract tests for new structure.
- Release bar: registry, fast, rendered, and screens tiers green on the
  integration branch, plus a fresh-agent reader review (screens pack plus
  the CLAUDE.md rule-5 questions only). High findings gate the release, and
  every finding gets a recorded disposition.

## Reproduction on `main` (2026-09-23, `c356a78`)

The screens pack (69 pages) plus five award sub-pages were captured into
the session scratchpad. Every item still reproduces, except as noted.

| # | Item | Still reproduces? | Owner |
|---|---|---|---|
| 1 | Step rendering and cadence caption | Partly. The cumulative chart is already stepped (H/V path). The per-period chart still draws sloped lines between submissions. No cadence caption exists. | Agent |
| 2 | Metric-identity audit | Done: `docs/reviews/evidence-2026-09-23/stage2/item2-metric-identity-audit.md`. Three label findings, plus one coordinator finding; none needs the owner | Agent |
| 3 | Tab purity | Yes. The award root carries obligation tiles and the obligation-account table. | Owner (conflicts with the decision-4 placement) |
| 4 | Empty File C placeholder | Yes, and wider than reviewed. 118 obligation pages show an empty current-FY table with only a "Show N more" toggle. 260 omit both sections entirely. | Agent |
| 5 | Correction-pair callouts | Changed. The Navy and Commerce "pairs" are the data defect below (#88), not source corrections. The CISA FY2023 P3/P4 pair is real and has a curated note. | Agent (display), data fix separate |
| 6 | Sentinel identity and age wording | Yes. 159 of 176 episodes share 36 titles; the headings omit the account and fiscal year. | Owner |
| 7 | All-years vs FY-to-date on the landing page | Yes: "$2703.529B net obligations across 502,002 distinct linked awards" with no horizon. | Agent |
| 8 | DHS CISA R&D decline | Data question answered (see memo) | Owner (caption) |
| 9 | Staleness marker reaches the numbers | Yes (structural; no unit is stale on `main`, so it is verified on a staged scenario) | Agent; stamp qualifier to the owner |
| 10 | Raw validator text in the warnings banner | Yes, and live now. The root, NSF, BIO, and CSE pages show a red "Data quality warnings" banner whose only content is the rollup's de-duplication notice. | Owner |
| 11 | Partial current month in "Awards per month" | Yes. DMS 175 → 6, and September is normally NSF's heaviest month. | Agent |

## Out-of-scope data defect: issue #88

While checking item 5, the coordinator found that 88 of 368 covering
`reportingPeriods` rows disagree with `cumulative(this) − cumulative(last
reported)`. The worst case is `dod/navy-rdte` FY2024 P12, shown as −$25.05B
where the cumulative series implies +$4.15B. `fyCumulative` and the FY
totals are correct. The cause is `aggregate()` building a covering row from
its own period's events only, which drops the File B activity that W14's
dollar-transient periods keep under their own label. Filed as issue #88 and
queued as a separate data-fix task. It is not fixed here (display only).
Stage 2's final reader review waits on it; without the fix, the Navy RDT&E
period chart shows a −$25B single period.

## Owner memo (sent 2026-09-23)

The owner memo text is below. Outcomes are recorded under "Decisions" once
the owner replies.

> **Stage 2 display batch: decisions needed.** ★ marks the recommended option. Reply with letters or edits. Agent-owned items proceed in the meantime.
>
> **0. FYI: data defect found (#88), outside Stage 2.** 88 published "Obligations by reporting period" rows are wrong: every row that "covers" a skipped period omits that period's activity. Navy RDT&E FY2024 P12 shows −$25.05B; the true value is +$4.15B. Cumulative charts and FY totals are correct. ★ Fix it in a separate data session, which I have queued: an offline rebuild plus a new validator invariant. It changes published period rows (layer d), so you see the diff before it merges. Stage 2's final reader review waits for it.
>
> **1. Item 3, tab purity.** This conflicts with the decision-4 placement.
> A★ The award root drops the obligation tiles and the obligation-account table. One cross-link card replaces them, carrying the decision-4 sentence verbatim, the existing "separate from, and not additive to" sentence, and a link. No obligation dollars appear on the award tab. The coverage line stays.
> B Keep them, but move them below all award content.
> C No change.
>
> **2. Item 6, sentinel.**
> 6a, the age counter ("unreviewed for 296 days"):
> A★ Drop the counter. The "Unreviewed signal" badge and the observation dates remain. This revises the decision-5 display.
> B Show "unreviewed since 2025-11-30" instead, a date rather than a count.
> C Keep decision 5.
> 6b, repeated titles (159 of 176 cards share 36 titles; the two "National Environmental Satellite Service" cards are NOAA PAC and NOAA ORF, so they are different accounts, not duplicates):
> A★ Add account and fiscal year from structured fields: "National Environmental Satellite Service · NOAA PAC · FY2026".
> B Group same-title cards.
> C No change.
>
> **3. Item 8, DHS CISA R&D decline.** The ledger matches the source's GTAS/File A totals exactly (FY2019 $16.34M, FY2024 $3.31M, FY2025 $98, FY2026 $0.79M through P10), so the decline is not a pipeline artifact. Whether the activity ended or moved to another account is not established: the AAAS crosswalk maps the line only to 070-0805.
> A★ A source-figure caption with no cause, following the periodNotes precedent: "The source reports $3.31 million for this account in FY2024 and $98 in FY2025. Source figures alone do not show whether the activity ended or moved to another account."
> B No caption.
> C Research a successor account first (a scope expansion).
>
> **4. Item 10, warnings banner.** This is live now: the root page's red "Data quality warnings" banner contains only "4 awards appear in more than one division; counted once in this rollup". That notice reports correct handling, not a problem.
> A★ (i) Move de-duplication notices, verbatim, to the neutral "Data quality notes" block. (ii) Real warnings keep the red banner, each led by a plain line, with the raw text in a "technical detail" disclosure:
> - shrink: "The stored award count went down since the previous pull. Stored awards are never deleted, so this flags a pipeline problem, not cancelled awards."
> - retained: "Some awards already on record were not returned by the latest pull; they are kept, not removed."
> - baseline: "A month's count came in below an independently verified tally; that month may be incomplete."
> - other: "An automated consistency check flagged this pull; technical detail below."
> B (i) only.
> C No change.
>
> **5. Rollup stamp qualifier (item 9 / W17, Medium).**
> A★ When a unit is stale, append to the rollup stamp: "· includes 1 unit last refreshed September 21, 2026 †" (the count and date are derived).
> B No stamp change; rely on the new † markers on the tiles and cells.
>
> **FYI, no decision needed unless you object:** Item 1's caption renders verbatim, lowercase-initial like the methodology line. Item 11 uses a dashed segment and an open marker, labelled "6 · Sep 2026 to date", with the caption "The last point is the current month to date — a partial count, drawn dashed with an open marker." Item 5 marks only periods that carry a curated source-figure note and points to that note; it uses no "correction" wording and no axis clipping. Item 9's markers reuse the existing † and the pipeline-written reason text only.

## Decisions

(pending)

## Log

| When (UTC) | Event |
|---|---|
| 2026-09-23 | Integration branch `claude/stage2-display` cut from `main` `c356a78` and pushed. Screens pack captured on `main`; every item checked. Issue #88 filed. Owner memo sent. Item 11 (Sonnet worker) and the item 2 audit (Sonnet, read-only) started. |
| 2026-09-23 17:20 | Item 11 committed (`43356d2`): dashed segment and open marker for the in-progress month; the screens tier gains award sub-pages. Fast 7/7, rendered 4/4. Item 2 audit committed (`2024359`): 3 label findings, plus 1 coordinator finding (count nouns). PR #89 opened into `claude/stage2-display`. |
| 2026-09-23 17:33 | Items 1, 5, and 2's fixes committed (`5b796c2`): step geometry, the owner's cadence caption verbatim on both obligation period charts, "see note" guides on the two curated periodNotes periods, "Net" in the title, the "Award $" header, "($)" in the legend, provider count nouns in chart titles, and a label halo. Pushed to PR #89. Fast and rendered re-running on `5b796c2` in a scratch worktree. |
| 2026-09-23 17:50 | Items 4 and 7 committed locally (`03da1f8`): "No File C rows linked to public awards in FY…" placeholders (the "shown first" sentence is dropped when it would promise missing rows), and "…, FY2017–FY2026 combined" on the all-years stamp. Item 9 worker started against the pipeline-generated stale scenario (scratch worktree: `nsf/mps/dms` stale since 09-21, `doe/sc` since 09-15). |
