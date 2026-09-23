# Stage 2b display follow-ups: handoff record

Running record for ledger items 12 and 14–22 (`docs/display-improvements-ledger.md`,
"Stage 2b queue"). A cold start reads this file, then `CLAUDE.md`, then the
ledger. Item 13 (NIH disclosure) shipped in PR #94 and belongs to Phase 3.2e
(`session_018jr4gow6x6QP3Fqj5BEoq7`), which removes it in its final PR.

## Rules (from the coordinator brief)

- Display only, except item 15 (data work). Nothing that smooths,
  interpolates, or invents precision.
- Integration branch `claude/stage2b-display`, cut from `main` at `10f3974`.
  Item 15's CI re-pull runs on its own branch `claude/stage2b-army-repull`
  (commits there are evidence only; nothing from it merges unless the
  re-pull shows a data defect).
- File ownership: Stage 2b owns `site/index.html`, `tests/test_site_contract.py`,
  the sentinel display, `reference/dod_army_rdte_obligation_baseline.json`,
  and Army's `dashboard.json`. Phase 3.2e owns the registry, every other
  obligation baseline, `data/obligations/**` otherwise, adapters, scripts,
  and workflows; it also updates the 53/13 pin and deletes the NIH sentence.
- No merge to `main` Mon ~10:37 → Tue ~23:00 UTC (weekly reconcile window).
- Owner-pinned strings change only for the approved items.
- Release bar: registry, fast, rendered, screens green, plus a fresh-agent
  reader review; Highs introduced by Stage 2b gate; every finding gets a
  disposition. The owner authorized merging fully green PRs (2026-09-23).

## Items

| # | Item | Disposition |
|---|---|---|
| 12 | Obligation scope disclosure | Implement: approved sentence appended to the landing subtitle, before the NIH sentence (which stays last for 3.2e to delete). |
| 13 | NIH absence | Not Stage 2b (PR #94; 3.2e removes). |
| 14 | $0 program-activity wording | **No change** (owner-approved ★: no explanatory claim). Stage 2's neutral collapsed group stays as shipped. |
| 15 | Army RDT&E FY2022 path | CI re-pull of FY2022 (P02–P12; a custom pull always covers the FY through its final period) — see "Item 15" below. |
| 16 | Source-only sentinel cards | Implement as approved. |
| 17 | Sentinel vs ledger "net" | Implement as approved. |
| 18 | Source descriptions shown as titles | Implement: flow-table descriptions rendered as quoted, cited "source description". |
| 19 | Oct–Nov 2025 low award counts | Implement with the CRS-verified end date (owner approved the memo's recommendation 2026-09-23): "October 1 – November 11, 2025 was a lapse in federal appropriations; award counts in those months are low." Beside the monthly and both cumulative award charts. |
| 20 | Root tile heading | Implement: "Award activity (NIH and NSF)". |
| 21 | Sentinel source status / process text | Implement as approved. |
| 22 | Supplemental / one-time money | **No change** (owner-approved ★: any tag would attribute cause). |

## Item 15: Army RDT&E FY2022

Pre-re-pull state on `main` `10f3974` (committed FY2022 partition accepted
2026-08-28; File B rows per period P02..P12 = 219, 218, 288, 220, 216, 218,
292, 293, 296, 317, 318; File C 1,944 rows). Every period is full-row
(not a stub like the DoD FY2025 P11 case). Cumulative net obligations
($B): P02 13.99, P03 16.26, P04 24.10, P05 28.07, P06 30.96, P07 74.05,
P08 75.92, P09 81.74, P10 49.86, P11 50.47, P12 52.53 (= GTAS pin
$52,527,159,204.06 exactly). Period rows: P07 +$43.09B, P10 −$31.88B.

Re-pull: run 35928876011 on `claude/stage2b-army-repull`, dispatched
2026-09-23 22:32 UTC via the trigger file (mode custom, `dod/army-rdte`,
FY2022, period 12).

## Item 19: lapse dates

The approved text says "October 1 – November 12, 2025 was a lapse in federal
appropriations". CRS R48765 ("Overview of Continuing Appropriations for
FY2026 (Division A of P.L. 119-37)") states that P.L. 119-37, signed
November 12, 2025, "ended a 42-day lapse in appropriations … lasting from
October 1, 2025, through November 11, 2025" (read via a search-index excerpt;
congress.gov, govinfo.gov, and everycrsreport.com are blocked from this
container). 42 days is Oct 1–Nov 11 inclusive, so the excerpt is internally
consistent. The end date differs from the approved text by one day, so per
the brief nothing is published and the owner gets a memo.

## Log

| When (UTC) | Event |
|---|---|
| 2026-09-23 22:30 | Integration branch cut from `main` `10f3974`. Item 15 re-pull pushed (run 35928876011). |
| 2026-09-23 22:40 | Item 19 check: CRS gives Oct 1–Nov 11; held for owner memo. Items 12, 16, 17, 18, 20, 21 handed to one Sonnet worker. |
| 2026-09-23 22:58 | Worker committed items 12, 16, 17, 18, 20, 21 (`7340bbe`): contract tests 59/59, fast 7/7, registry 382/382; rendered 3/4 because `scripts/smoke_sentinel_page.py` pinned the pre-item-17 state line. |
| 2026-09-23 23:10 | Coordinator: smoke markers updated to the approved 16/17 wording (and the retired "eight weeks" line added to its retired list — a sentinel-display test, so Stage 2b's, not a 3.2e pipeline script); `humanDateOnly` pinned to UTC so a check near midnight UTC can't show the previous day. Rendered 4/4. |
| 2026-09-23 23:20 | Owner approved the item-19 memo recommendation (Nov 11). Implemented beside the award monthly and cumulative charts; contract test added; before/after captures `item19_*`. |
