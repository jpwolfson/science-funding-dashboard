# Ledger item 2 audit — metric identity on charts/tiles/tables

Scope: every chart, tile group, and table must state its metric (award
count vs award dollars vs signed obligation dollars) in its title or axis
— not only in a note — and must agree with the tab/section it sits under.

Method: full read of `award-root.png`, `obligations-landing.png`,
`sentinel.png` (cropped into strips), the five award sub-pages
(nsf, nsf/mps, nsf/mps/dms, nih, nih/nci — via their `.txt` renders, which
are exact page text, cross-checked against the PNGs), six obligation
account pages in full (dod-navy-rdte, doe-sc, commerce-nist-its,
dhs-cisa-rd, nsf-rra, nasa-science), four PA pages in full
(doe-basic-energy-sciences, dod-basic-research,
hhs-administration-for-strategic-preparedness-and-response,
nasa-science-direct), and a 66-page contact-sheet skim of every remaining
account/PA page's top section (tiles + first table) for template
deviation. Every title/axis/legend/header string below is quoted from
`site/index.html` (read-only) with line numbers, cross-checked against the
rendered screenshots/text. No file in the repo was modified.

## 1. Findings table

| Page type(s) | Element (exact title) | Metric actually plotted | Where metric is stated | Tab/section identity | Verdict | Finding detail / minimal fix |
|---|---|---|---|---|---|---|
| award-root, agency (NSF/NIH), directorate, division | Tiles: "Awards, FY## Oct–Jul" (root) / "New awards, …" (NSF) / "Award records, …" (NIH) | Award **count** | Label (no $) + plain-number value | Award dashboards | OK | `countLabel` at index.html:758 varies correctly by provider; value uses `fmtN` (no $). |
| same | Tiles: "Award $, …" (root/NIH) / "Intended $, …" (NSF) | Award **dollars** | Label carries "$" + `fmtM` value (`$…B/M`) | Award dashboards | OK | index.html:759, 763. |
| same | Tiles: "Standard grants"/"Continuing grants" (NSF), "New/competing awards"/"Noncompeting continuations" (NIH), "New/standard awards"/"Continuing awards" (root) | Award **count** by mechanism | Label + plain-number value | Award dashboards | OK | index.html:764-765, `DEFAULT_MECHANISMS` (line 192); mixed-label root confirmed on-screen (award-root.png tile row 3–4: "New/standard awards, Oct–Jul" 13,212 / "Continuing awards, Oct–Jul" 28,776). |
| all award-ledger pages | "Cumulative awards through the fiscal year" | Award **count**, FY-to-date | Axis (plain numbers, no $); title uses "awards" | Award dashboards | OK | index.html:2179-2181. |
| all award-ledger pages | "Cumulative award dollars through the fiscal year" | Award **dollars**, FY-to-date | Title says "dollars"; axis `$0M…$Nb` | Award dashboards | OK | index.html:2182-2184. |
| all award-ledger pages | "Awards per month" | Award **count** | Axis plain numbers; table cols "Month, Awards, Award $" | Award dashboards | OK | index.html:805, 859-860. |
| all award-ledger pages | "Awards by fiscal year (Oct–Jul)" | Award **count** | Axis plain numbers; hairline label "FY15–24 avg 8517" (no $) | Award dashboards | OK | index.html:866, 883. |
| all award-ledger pages | "Awards by mechanism (Oct–Jul)" | Award **count** by mechanism | Axis plain numbers; legend/line labels match mechanism labels (counts, no $) | Award dashboards | OK | index.html:923, 972. |
| all award-ledger pages | "Award dollars by fiscal year" | Award **dollars**, split top-3 vs rest | Title says "dollars"; axis `$0M…$N B` | Award dashboards | Finding (minor) | Chart **legend** swatches read "All other awards" / "Top 3 awards" (index.html:1019) — count-shaped nouns ("awards") on a dollar series, with no `$` or value in the legend itself; only the title/axis carry the `$`. Matches the audited failure class ("count-language in a chart key or legend for a dollar series") even though the title/axis do disambiguate. Minimal fix: restate as "All other awards' $" / "Top 3 awards' $", or move a `$` into the swatch text, e.g. "Top 3 awards ($)". (Table headers for the same split — "Total award $ / Top 3 awards / All other / Median award", index.html:1020 — are **not** flagged: every dollar cell in every table sitewide self-labels via an inline "$" per the site's established convention, e.g. obligation tables' "Net obligations"/"File C portion" headers carry no $ either but every cell does.) |
| all award-ledger pages | "Largest awards, last three fiscal years" table | Award **dollars** per award (4th column) | **Not stated anywhere** — 4th `<th>` is `""` (blank) | Award dashboards | **Finding** | index.html:1105: `["FY", "Award", "Institution", ""].forEach(...)`. Every other table on the site labels every column (even count columns get a bare name like "Awards"); this is the only column on the whole site with **no header text at all** — confirmed blank in the rendered table (award-nih.png / award-nsf.png "Largest awards" table: header row reads "FY / Award / Institution" then a blank cell above the `$43.1M`-style values). The `$` prefix is visible per-cell, so the metric is not truly hidden, but it is the one header that states nothing. Minimal fix: give the 4th `<th>` the text `"Award $"` (matching the tile/table label used everywhere else for this exact figure). |
| award-root only | Root obligation tile group heading | (heading, not a number) | — | Sits directly under "Award activity" tiles, before its own "Appropriations obligations" heading and a note that starts "Obligations from … federal accounts … They are **separate from, and not additive to, the award totals above**." | OK | index.html:2144-2158 (`heading: \`${obligationScope} obligations\``, i.e. "Appropriations obligations" when the root has >1 obligation child, confirmed on screen). Clearly distinct heading + explicit non-additivity disclaimer sitting right at the award/obligation boundary — the one place on the site where the two ledgers are adjacent, and it is the best-labeled boundary on the site. |
| award-root only | "Appropriations obligation dashboards" children table | Signed **obligation** dollars (`Net obligations FY#### to date`), File C/net ratio, distinct linked awards | Column header states "Net obligations …"; note reiterates "separate from award totals" | Sits under Award dashboards tab, but is explicitly an obligation-ledger preview | OK | index.html:2166-2167. |
| award-root, agency, directorate | "Directorates"/"Institutes & centers"/"Divisions & offices" children table | Award **count** + award **dollars** (two columns) | Headers: "Awards Oct–Jul FY####" (count) / "Award $ Oct–Jul" (dollars, explicit $) / "Total awards since 2014" (count) | Award dashboards | OK | index.html:492, 656. |
| obligations-landing, every account, every PA page | Tile: "Net obligations, FY#### to date" | Signed net **obligation dollars** | Label says "obligations"; value `fmtSignedMoney` (`$…B`, signed) | Appropriations obligations | OK | index.html:1159. |
| same | Tiles: "Positive ledger entries, …" / "Negative ledger entries, …" | Signed **obligation dollars** (gross positive / gross negative activity) | Value carries "$" (fmtSignedMoney); label itself says "entries" (a count-shaped noun) with no $ or "obligations" | Appropriations obligations | OK (see note) | index.html:1160-1161. The word "entries" is count-shaped, but the value under it is always rendered with a "$" (e.g. "$302.817B"), which is the site's uniform disambiguation pattern for every dollar figure — not flagged as a Finding, but noted because it is the closest near-miss to the audited failure class among the tiles. |
| same | Tile: "Distinct File C-linked awards, FY#### to date (not new awards)" | Award **count** | Label; plain-number value (`fmtN`) | Appropriations obligations | OK | index.html:1162. Parenthetical explicitly heads off the most likely misreading (as a count of new awards). |
| same | Tiles: "File C portion, … (X% of net)" / "File B − File C residual, …" | Signed **obligation dollars** | Value carries "$" | Appropriations obligations | OK | index.html:1165-1167. |
| obligations-landing, every account, every PA page | "Cumulative net obligations through the fiscal year" | Signed **net obligation dollars**, FY-to-date | Title says "net obligations"; axis signed `$` (crosses `$0K` with negative territory shown, e.g. commerce-nist-its) | Appropriations obligations | OK | index.html:1188. |
| **obligations-landing, every account, every PA page** | **"Obligations by reporting period"** | Signed **net obligation dollars** per period (single-value line, positive and negative, e.g. −$8.6M on 2022P12 in dod-navy-rdte) | Axis is signed `$`; but the **title omits "net"** even though the value plotted is exactly the same net-obligations concept as the two sibling charts, both of which do say "net" | Appropriations obligations | **Finding** | index.html:1282: `makeCard("Obligations by reporting period", "Each point is signed activity in one agency submission period…")`. The word "net" only appears in the note (not the title) and in the tooltip/table ("net obligations" in tooltip line 1335 and table header line 1360). This is a real title/note split: the metric name is disclosed in the note and downstream table, not the chart's own title, and it is inconsistent with its two siblings ("Cumulative **net** obligations…", "**Net** obligations by fiscal year") which state the same word in-title. A reader skimming titles only would not see "net" here. Minimal fix: rename the title to **"Net obligations by reporting period"** (one string change at index.html:1282, applies uniformly to all 67 obligation pages since it is one shared function). |
| same | "Net obligations by fiscal year" | Signed **net obligation dollars** per FY | Title says "net obligations"; axis signed `$` | Appropriations obligations | OK | index.html:1371. |
| every account/PA page | "Program activities" children table | Signed **net obligation dollars** + File C/net ratio + distinct linked awards | Header: "Net obligations FY#### to date" (explicit) / "File C / net" (%) / "Distinct linked awards" (count) | Appropriations obligations | OK | index.html:562-563. |
| obligations-landing (agency-level rollup) | "Agencies" children table | same as above | same headers | Appropriations obligations | OK | index.html:492 reused pattern via obligationChildrenCard — confirmed identical header set on screen. |
| obligations-landing, account, PA (when recipients exist) | "Top recipients of award-attributed obligations" | Signed **net award-linked obligation dollars**, ranked | Column header: "Net award-linked obligations" (explicit, $ values) | Appropriations obligations | OK | index.html:1450, 1464-1465. |
| obligations-landing, account, PA (when flows exist) | "Largest award-attributed gross flows" | Signed **obligation dollars** per award-linked File C entry, with a separate "Direction" column | Column header: "Amount" (explicit; "Direction" col separately says "Positive entry"/"Negative entry") | Appropriations obligations | OK | index.html:1492-1493. |
| obligations-landing only | Landing stamp line | Signed **net obligation dollars** total + distinct linked awards (count) across all registered accounts | Stamp text itself: "…net obligations across …distinct linked awards · through FY####P## …" | Appropriations obligations | OK | index.html:2074-2075 — states "net obligations" explicitly in the stamp, the most prominent line on the page. |
| sentinel | Tiles: "Episodes" / "Unreviewed signals" / "Source-confirmed" / "Reviewed / restored" | Episode **count** | Plain-number value (`fmtN`); heading "Episode status" | Funding-action sentinel | OK | index.html:1727-1742. |
| sentinel | Episode card header figures ("$X gross negative · $Y net") and fact row | Signed **dollar** figures (cents-derived, `fmtCents`→`fmtSignedMoney`) | Inline in the heading itself, always with "$" and the words "gross negative"/"net" attached | Funding-action sentinel | OK | index.html:1849-1873. |
| sentinel | "Authoritative source freshness" table | Non-financial: status/date/record **count** | Header: "Records" (explicit, count) | Funding-action sentinel | OK | index.html:1756-1757. |
| sentinel | Financial-observation lines inside an episode ("FY2026P10: portfolio cluster rule; $X gross negative and $Y net activity.") | Signed **dollar** figures | Inline, always "$" + "gross negative"/"net activity" | Funding-action sentinel | OK | index.html:1878-1879. |

## 2. Needs owner decision

None. Every finding above is a pure label/title restatement of the metric
already being computed and displayed (no finding proposes counting
anything differently, changing what a number is, or touching measure
semantics). Per the audit's own framing, none of these rise to the
"what a number claims to be" tier that would need owner sign-off — they
are all "the number is right, but one of its four label surfaces (title /
axis / legend / table header) doesn't say what it is, though a sibling
surface on the same element does."

## 3. Tooltip/legend mismatches (from site/index.html, since tooltips aren't in the screenshots)

- No tooltip states a different metric than its chart. Checked every
  `showTip(...)` call for the six award charts and three obligation
  charts: all count tooltips use `fmtN` and count-shaped labels ("awards
  Oct–Jul", "awards full FY", "standard"/"continuing"/"fellowships"
  lowercased); all dollar tooltips use `fmtMoney`/`fmtM`/`fmtSignedMoney`
  and dollar-shaped labels ("award dollars", "total award dollars", "top
  3 awards" [$ value], "net obligations", "File C portion", "residual").
- The one legend flagged above ("All other awards" / "Top 3 awards" on
  "Award dollars by fiscal year", index.html:1019) is the only
  legend/key on the site using a count-shaped word ("awards") to label a
  swatch that represents a dollar series with no `$` in the swatch text
  itself. Listed as a Finding in §1, not repeated here.
- No other legend (mechanism chart's "Standard grants"/"Continuing
  grants"/"Fellowships", index.html:971; obligation cumulative chart's
  "FY##" per-line legend, index.html:1266) carries the wrong metric word
  for its series.

## Files referenced (read-only; nothing in the repo was modified)

- `/home/user/science-funding-dashboard/site/index.html` (all line
  numbers above)
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/screens/award-root.png`
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/screens/obligations-landing.png`
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/screens/sentinel.png`
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/screens/obligations-account-{dod-navy-rdte,doe-sc,commerce-nist-its,dhs-cisa-rd,nsf-rra,nasa-science}.png`
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/screens/obligations-pa-{doe-basic-energy-sciences,dod-basic-research,hhs-administration-for-strategic-preparedness-and-response,nasa-science-direct}.png`
- `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/before/award-pages/{award-nsf,award-nsf-mps,award-nsf-mps-dms,award-nih,award-nih-nci}.{png,txt}`
- 66-page contact sheet of all remaining obligation account/PA page tops:
  `/tmp/claude-0/-home-user-science-funding-dashboard/c9973df0-5062-566f-a5a4-b931d5cfd521/scratchpad/item2/contact_accounts_{00,01,02}.png`

## Coordinator dispositions (2026-09-23)

The audit ran on `main` at `c356a78`. Line numbers above refer to that tree.
Every finding was re-checked against the source.

| Finding | Disposition |
|---|---|
| "Obligations by reporting period" title omits "net" | Fix: retitle it "Net obligations by reporting period", matching its two sibling charts (items 1+5 cluster, same function). |
| "Largest awards" table has a blank dollar-column header | Fix: header "Award $", the site's existing label for this figure. |
| "Award dollars by fiscal year" legend uses count nouns | Fix: "All other awards ($)" / "Top 3 awards ($)". |
| Not flagged by the audit: count charts say "awards" on every provider, while the tiles say "New awards" (NSF), "Award records" (NIH), or "Awards" (root) | Fix: count-chart titles reuse the tiles' provider-aware `countLabel`, so a chart and the tile above it name the same count. This only restates the label that already exists; no count changes. |
| Nothing needs an owner decision | Agreed. Every fix restates a metric that is already computed and displayed. |
