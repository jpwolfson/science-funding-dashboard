# Handoff: cumulative FY-to-date overlay charts

Port of a feature built and shipped on fed-funding-dashboard (commit
`1c1fba4`, live at https://jpwolfson.github.io/fed-funding-dashboard/ —
look at the first two charts before starting). This document is the full
spec plus every design decision and pitfall already paid for there, so
implementation here is mechanical. **Intended execution: one Sonnet
implementation pass + a parallel Sonnet verification sweep. Fable only for
final review.** No API access is needed at any step — this is pure
re-aggregation of committed data plus front-end.

## What and why

Two charts on every node page, leading the chart sequence — first and
second cards after the summary tiles, with all existing charts following
in their current order (owner-confirmed placement, fed-funding-dashboard
commit `2c211a0`):

1. **Cumulative new awards through the fiscal year**
2. **Cumulative intended dollars through the fiscal year**

Each overlays the last 5 fiscal years as weekly cumulative lines, Oct 1 →
Sep 30. The year in progress ends exactly at the latest data date with its
value labeled at the endpoint. Purpose (owner's words): the monthly chart
makes you visually integrate area-under-curve to compare FY-to-date
positions; these charts give that number exactly, at every week of the year.

## Data contract

`aggregate()` in `adapters/common.py` gains one output key. Because
`scripts/rollup.py` calls the same `write_dashboard` → `aggregate`, adding
it in that one function covers every leaf, directorate, agency, and root
dashboard — do not implement it anywhere else.

```
"fyCumulative": [            // last 5 FYs ascending, current year last
  { "fy": 2026,
    "partial": true,         // fy == current FY
    "points": [              // weekly running totals
      { "d": 6, "awards": 3, "dollars": 120000 },   // d = day-of-FY, Oct 1 = 0
      ...                    // every d % 7 == 6, plus a final point at the
    ] }                      // last day (Sep 30, or today for the partial year)
]
```

Rules (each one matters):
- **Align by day-of-fiscal-year, not calendar week** — `d = (date − Oct 1
  of the FY).days`. This is what makes leap years and weekday drift unable
  to misalign the lines.
- Emit a point at every `d % 7 == 6` plus one final point at the series'
  last day. Complete years end at Sep 30; the partial year ends at the latest data date (the later of today and the newest award date - NIH notice dates can post-date the pull).
- The stored partial-year endpoint may therefore include future-dated NIH
  award notices. The browser must clip the visible current-year line and table
  to the dashboard's `generated` date; those future records preserve the
  accounting invariant but must not visually extend a "to date" line.
- **Endpoint invariant (the acceptance test):** each complete year's final
  point must equal that year's `fiscalYears` entry `awards`/`dollars`
  EXACTLY; the partial year's final point must equal the current FY row.
  If they differ, the implementation is wrong — do not tolerance this.
- Reference implementation: fed-funding-dashboard
  `scripts/pull_nsf_dms.py`, the `fy_cum` block just above `out = {...}`
  (~25 lines, O(awards) per FY via a daily-bucket accumulator).

## Front-end

Reference: fed-funding-dashboard `index.html`, `cumulativeChart(data, key,
title, note, fmtVal, fmtEnd)` — a single function instantiated twice from
`boot()`. This site's chart scaffolding (`makeCard`/`frame`/`yAxis`/
`showTip`/`addTable`/`legend`) is the same lineage, so the function ports
nearly verbatim. Decisions already settled there — keep them:

- **Palette:** extend to five series slots. These exact hexes were
  validated with the dataviz skill's `validate_palette.js` against this
  site's surfaces, both modes, all checks passing:
  light `--s4: #eda100; --s5: #e87ba4`, dark `--s4: #c98500; --s5: #d55181`
  (added to all three CSS theme blocks). Slot order newest→oldest:
  current FY = `--s1` … FY−4 = `--s5`. Light-mode contrast for s3/s4/s5 is
  below 3:1, which is legal only because every line carries a direct label
  and a table view exists — do not drop either.
- **Draw order:** oldest first, so the current year paints on top; current
  year gets `stroke-width: 3` and a larger endpoint dot, others 2.
- **Endpoint labels:** the current year's label sits at its endpoint
  (`FY26 · 585` style, via `fmtEnd`). Completed years' labels sit in the
  right margin **sorted by endpoint value with a ≥15px collision push and
  a short color-key dash before each label**. The naive version (label at
  each line's own y, nudged in draw order) shipped first and put FY23's
  1,015 label below FY22's 979 — visually wrong. The sort is the fix;
  right pad 122px so dollar labels don't clip.
- **Axis:** x spans 365 days; month labels Oct…Sep centered at offsets
  `[0,31,61,92,123,151,182,212,243,273,304,335]+15`, month-boundary ticks
  in `--axis`, **weekly minor ticks** (every 7 days, 3px, `--grid`) — the
  owner asked for weekly ticks specifically. One y-axis per chart (awards
  count / dollars), never dual.
- **Hover:** full-height crosshair snapped to week index
  `wi = min(floor(day/7), 52)`; tooltip head `Week N · through <Mon D>`
  (render the day-of-FY in a fixed non-leap reference year); one row per
  year that has reached that week (filter, don't show blanks).
- **Table view (`addTable`):** month-end cumulative rows Oct…Sep, one
  column per FY. For the partial year print values only for months whose
  START day-of-FY ≤ its last data day, else `—` — so unstarted months
  read as em-dash and the current month row shows the through-today value.
- **Wire into `boot()`** guarded by `data.fyCumulative?.length`, as the
  FIRST entries in the `renders` array (before the monthly chart) so the
  two cards lead the page; keeping them in `renders` is what makes
  resize/theme re-render work.

## Repo-specific adaptations (the only new thinking required)

1. **Sparse and dormant units.** 19 units are dormant; some leaves will
   have all-zero or nearly-zero cumulative series. Reuse this site's
   existing zero-data guards (`chartMax` etc.): if every series endpoint is
   0, skip both cards entirely (consistent with how sparse units already
   suppress content). Never feed max=0 into `niceTicks`.
2. **Regeneration without API access.** Leaf dashboards are written at
   pull time, but this feature needs no pull: add an offline
   re-aggregation path (fed-funding-dashboard added an `--offline` flag to
   its pull script; here a small `scripts/reaggregate.py` that loads each
   leaf's `awards.csv` and calls `write_dashboard`, then runs rollup, fits
   the existing layout better). The dev environment has no NSF egress, but
   this runs anywhere. Regenerate all leaves + rollups in one commit.
   `today` for offline re-aggregation = date of run; the weekly CI run
   refreshes it naturally thereafter.
3. **Rollup scale:** root node is ~138k awards × 5 FYs; the daily-bucket
   accumulator is O(awards + 365·5) per node — fine. Don't quadratic it.

## Acceptance checklist (all mechanical — parallel Sonnet sweep)

- [ ] Endpoint invariant holds for **every** `dashboard.json` in `data/`
      (write a checker script; run over all ~75 nodes; zero failures).
- [ ] `verify_dms_baseline.py` still green (aggregation change must not
      perturb existing keys).
- [ ] Browser check (Playwright + `/opt/pw-browsers/chromium`, light AND
      dark `colorScheme`): root, one agency, one directorate, DMS
      (`nsf/mps/dms`), one dormant/sparse unit. Zero console errors; no
      clipped or mis-ordered endpoint labels; tooltip shows all active
      years at one week; table `—` logic correct on the partial year.
- [ ] Screenshot both new charts on DMS and compare numbers against
      fed-funding-dashboard's live versions (same underlying division —
      values should match that repo's current data).
- [ ] Site diff touches only: `adapters/common.py`, `site/index.html`,
      new `scripts/reaggregate.py`, regenerated `data/**/dashboard.json`.
      `awards.csv` files must be byte-identical (re-aggregation reads,
      never rewrites, stores).

## Definition of done

All checklist items green, committed to a `claude/**` branch, PR to main
merged (deploy fires from main), CLAUDE.md roadmap updated to check this
item off, and the live site shows the two charts on every non-sparse node.
