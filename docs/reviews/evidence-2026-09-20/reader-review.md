# Reader review — 2026-09-20

**Reviewer context:** This review was performed with NO build context. The
reviewer did not read any repository code, documentation, commit history,
or prior reviews, and did not ask what the site is for. The only inputs
were the rendered page screenshots listed below (full-page PNGs, light
mode, 1100px wide), read directly as images (tall images were split into
vertical strips or cropped for close inspection; no content was skipped).

**Files reviewed** (from `/tmp/screens-2026-09-20/`):
1. `award-root.png`
2. `obligations-landing.png`
3. `obligations-account-dod-navy-rdte.png`
4. `obligations-account-dod-defense-wide-rdte.png`
5. `obligations-pa-dod-basic-research.png`
6. `obligations-account-commerce-noaa-orf.png`
7. `obligations-account-commerce-nist-its.png`
8. `obligations-account-doe-sc.png`
9. `obligations-account-dhs-cisa-rd.png`
10. `sentinel.png`

All ten files were present; none were missing.

---

## 1. award-root.png — "Federal science funding dashboard"

**(a) First-time-visitor takeaway.** This is a top-level rollup of federal
science funding across two agencies currently loaded (NIH and NSF), showing
44,798 awards and $27.847B for FY2026 to date, with year-over-year
comparison charts, cumulative FY-to-date lines, and a "largest awards"
table. It reads as a live, self-describing dashboard with its own data
caveats spelled out at the top and bottom.

**(b) Most misleading possible reading.** A reader could compare the
FY2026 line (still in progress, cut off at "Oct-Jul") directly against the
completed FY2022–25 lines in the "Cumulative awards" and "Cumulative award
dollars" charts and conclude funding is falling every year in a straight
line, without registering that FY2026 is a partial year still accruing
(the page does caption this, but only in smaller print: "Running Fri-to-date
… one line per year. Year in progress against that same point in prior
years").

**(c) Claims/labels that may over-state.** None found that clearly exceed
the data — the page is unusually well-hedged (see "How to read this" at
bottom, and inline notes on mechanism churn, deobligation, and source
completeness). One soft spot: the "Awards by fiscal year" bar chart caption
says "so the current year compares like-for-like," which is correct only
because the comparison bars are also truncated to Oct-Jul; a reader who
misses that could still compare FY2026's partial-year bar to what looks
like a normal full-year bar for FY22 without noticing both are Oct-Jul.

**(d) Specific text checks.**
- "Award-level detail is sparse" — not present on this page (this is a
  DOD-obligation-ledger note, not shown on the award dashboard).
- "Award ledger:" — present, verbatim: **"Award ledger: NIH and NSF, 87
  units."**
- "Obligations from" — not present on this page.
- "not reported at pull" — not present on this page.
- "counts as of the pull date" — not present on this page.
- Hollow/open marker on a cumulative line — none visible on this page's
  cumulative charts.
- "counts as of the pull date" — absent (see above).

**(e) Chart/table anomalies.** The "Awards per month" sparkline-style chart
dips to a labeled **"6,477"** near the right edge (looks like a partial or
low month) without an accompanying explanation on this page of why the
final visible month is so much lower than the surrounding noisy series —
a reader could read that as a funding collapse rather than a not-yet-complete
month. No other collapse-to-zero or mid-year spike found in this page's
charts.

---

## 2. obligations-landing.png — "Federal science obligation dashboard"

**(a) First-time-visitor takeaway.** This is the parent index for a
second, separate dataset — USAspending-sourced obligations — covering 53
federal accounts across 13 agencies, with a big top-line "$285.826B" net
obligations figure, a per-agency table, and multi-year cumulative/annual
charts. It presents itself explicitly as different from the award-level
dashboard ("not award totals, appropriations, or outlays").

**(b) Most misleading possible reading.** The per-agency table ranks
agencies by "Net obligations FY2026 to date" with a "File C / net" percentage
column that ranges from 0.0% (DOD) to 97.0% (ED). A reader skimming only the
dollar column, without reading the note directly below the table (which
does explain this), could treat DOD's $206.076B as somehow less real or
less complete than, say, NASA's $15.811B, when the page's own note says the
opposite ("the File B account total is complete").

**(c) Claims/labels that may over-state.** The subtitle line reads:
**"$2703.529B net obligations across 502,001 distinct linked awards ·
through FY2026P10 (July 2026) · last updated September 20, 2026. Obligations
from 53 registered science-related federal accounts, including defense
RDT&E."** The $2703.529B figure is a multi-year cumulative total (all
history, not FY2026), placed directly above the FY2026-specific $285.826B
card; a fast reader could conflate the two and believe FY2026 obligations
are $2.7 trillion.

**(d) Specific text checks.**
- "Award-level detail is sparse" — present, in the DOD agency-table
  footnote, verbatim: **"* DOD — Department of Defense: Award-level detail
  is sparse for Department of Defense accounts. Classified, intramural,
  interagency, and contract-heavy activity is not reported with equivalent
  public award detail in File C. A low File C share is an attribution
  limit, not evidence of missing or unobligated dollars; the File B
  account total is complete."**
- "Award ledger:" — not on this page (that's the award-root page's line).
- "Obligations from" — present, verbatim: **"Obligations from 53
  registered science-related federal accounts, including defense RDT&E."**
- "not reported at pull" — present, verbatim (chart caption): **"A period
  not reported at pull is omitted from the chart and shown in the table
  below."**
- "counts as of the pull date" — not found.
- Hollow/open marker — the cumulative chart caption states one exists
  ("A hollow point marks a period whose File B snapshot was not reported
  at pull"), and the FY2024 (green) line does show an open circle around
  Aug in this rendering.

**(e) Chart/table anomalies.** The "Net obligations by fiscal year" bar
chart shows '26 as a partial-year (lighter-shaded) bar noticeably taller
than several completed prior years (e.g., '19, '20) — correct for a
cumulative-obligation series that only grows, but combined with no y-axis
annotation marking which bars are partial vs. final, a fast reader could
read the tall '26 bar as "this year already exceeds those years" rather
than "this year is still accruing on top of an already-higher run rate."

---

## 3. obligations-account-dod-navy-rdte.png — Navy RDT&E

**(a) First-time-visitor takeaway.** Navy RDT&E obligated $28.100B in
FY2026 to date, essentially all of it (99.8%+) outside the linked-award
(File C) detail, consistent with the page's own note that DOD award detail
is sparse. Program-activity breakdown, multi-year cumulative chart, and
top-recipient tables are shown.

**(b) Most misleading possible reading.** Because File C portion is
"(-0.2% of net)" and $0/near-$0 in dollar terms, the "Top recipients" and
"Largest award-attributed gross flows" tables are populated (there are 10
recipients listed, e.g. HII Mission Technologies Corp $1.7M), which could
lead a reader to believe those tables represent Navy RDT&E's real award
mix, when by the page's own math the linked-award total shown in those
tables is a vanishingly small fraction of the $28.1B account total.

**(c) Claims/labels that may over-state.** None beyond the above; the
Interpretation Note is present and clearly worded.

**(d) Specific text checks.**
- "Award-level detail is sparse" — present verbatim (Interpretation Note,
  identical wording to the landing-page footnote).
- "Award ledger:" / "Obligations from" — not on this page.
- "not reported at pull" — present, verbatim, in the reporting-period chart
  caption.
- "counts as of the pull date" — not found.
- Hollow/open marker — **found and confirmed by close crop**: the FY2023
  (gold) cumulative line carries a visible hollow (open-center) circle
  marker around July, matching the caption's stated meaning (a period
  whose File B snapshot wasn't reported at that pull; the line holds the
  prior value flat through that point).

**(e) Chart/table anomalies — HIGH SEVERITY.** The "Cumulative net
obligations through the fiscal year" chart's **FY2024 (green) line spikes
from roughly $22B to roughly $46B around early August, holds that
elevated plateau for several weeks, and then drops sharply back down to
end the fiscal year at the labeled value of $29.563B.** This is a
genuine mid-year spike-then-collapse of roughly $17–20B (a swing on the
order of 60–70% of the year-end total) with no on-chart annotation
distinguishing it from real activity — it is neither explained as a
"not reported at pull" hollow point (that marker appears on the gold
FY2023 line, not the green FY2024 line) nor called out anywhere else on
the page. A reader who happened to view a cached or comparable version of
this chart in August would have seen Navy RDT&E FY2024 obligations at
~$46B, a figure never actually reflected in any final annual total.
Separately, the "Obligations by reporting period" chart shows a sharp
dip to roughly **-$120M** immediately followed by a spike to roughly
**+$150M** in the same neighborhood of periods — a large
negative-then-positive pair consistent with a correction cycle, again
without an inline callout.

---

## 4. obligations-account-dod-defense-wide-rdte.png — Defense-Wide RDT&E

**(a) First-time-visitor takeaway.** Defense-Wide RDT&E obligated
$44.907B in FY2026 to date across program activities like Advanced
Component Development ($11.361B) and Advanced Technology Development
($9.562B), with a File C linkage of only 1.0%, again flagged by the same
DOD interpretation note.

**(b) Most misleading possible reading.** Same pattern as Navy RDT&E: the
"Top recipients" table (Lockheed Martin $275M, Palantir $227M, etc.) looks
like a normal, complete leaderboard, but by the page's own stated File C/net
ratio (1.0%) it represents only about one percent of the account's actual
obligations — a reader unfamiliar with the note could treat Lockheed's
$275M as a large, representative share of a $44.9B account rather than a
sliver of the reported-detail slice.

**(c) Claims/labels that may over-state.** None beyond the recipient-table
framing above; the Interpretation Note is present.

**(d) Specific text checks.** Same verbatim Interpretation Note as Navy
RDT&E present; "not reported at pull" caption present; no "counts as of the
pull date"; no "Award ledger:"/"Obligations from" (not applicable to this
page level). No hollow marker was clearly visible in this particular
chart's visible line segments.

**(e) Chart/table anomalies.** Comparatively the most "normal-looking" of
the DOD pages reviewed: the cumulative lines for FY2022–26 rise in roughly
parallel steps from ~$29B to ~$45B without a dramatic spike-and-collapse.
The "Obligations by reporting period" chart does show one sharp dip to
roughly -$5M around period 2024P05 followed by recovery — much smaller in
relative terms than the Navy page's swing, and plausibly ordinary
correction noise rather than a standout anomaly.

---

## 5. obligations-pa-dod-basic-research.png — Army RDT&E → Basic Research

**(a) First-time-visitor takeaway.** This is a program-activity-level
drill-down (Army RDT&E, Basic Research) showing $417M obligated FY2026 to
date, $0 of which is File C-linked (0.0%), with zero distinct linked
awards.

**(b) Most misleading possible reading.** Because File C portion is
exactly $0 with 0 distinct linked awards, the "Top recipients of
award-attributed obligations" and "Largest award-attributed gross flows"
sections render as bare headers with only a "Show 20/40 more rows" toggle
and no visible rows above the fold — a reader could conclude the account
has no awards or no data at all, rather than "no award-level detail is
published for this line," which is what the Interpretation Note above
actually says.

**(c) Claims/labels that may over-state.** None literally false, but the
empty-looking recipient/flow sections without any inline "no data available
for this activity" placeholder text (only a collapsed "show more" affordance)
risk being read as missing/broken content rather than an expected DOD
data-sparsity outcome.

**(d) Specific text checks.** Same Interpretation Note verbatim as the
other DOD pages. "Not reported at pull" caption present. No "Award ledger:"
/ "Obligations from" lines (page level doesn't include them). No "counts as
of the pull date." No hollow marker clearly visible in the visible chart
region for this narrower program activity.

**(e) Chart/table anomalies.** The "Obligations by reporting period" line
shows one very sharp dip toward roughly -$20 to -$30M around mid-2025,
immediately followed by a tall spike to roughly +$130M shortly after — the
largest negative-then-positive pair (in relative terms, roughly 3x the
typical monthly amplitude of ~$40–50M) of the DOD pages reviewed. The
"Cumulative net obligations" chart itself, by contrast, looks smooth and
monotonic per year (FY23 $659M, FY24 $565M, FY25 $536M, FY22 $523M, FY26
$417M to date) — i.e., the sharp swing in the period chart nets out
without visibly disturbing the cumulative chart, which is good practice,
but nothing on the page tells the reader that connection explicitly.

---

## 6. obligations-account-commerce-noaa-orf.png — NOAA Operations, Research and Facilities

**(a) First-time-visitor takeaway.** NOAA ORF obligated $3.651B in FY2026
to date, with a much higher File C coverage than the DOD pages (82.4%
overall, per the parent-level table on other pages), broken into program
activities like ARRA-C ($1.474B) and National Weather Service ($723M), with
year-over-year cumulative and per-period charts and a recipient table
topped by "Coastal Protection & Restoration Authority of Louisiana"
($27.2M).

**(b) Most misleading possible reading.** Comparing the in-progress
FY2026 (blue) cumulative line against prior years' full trajectories, a
reader would reasonably conclude NOAA ORF is currently running behind
FY2022–25 at the same point in the year. That specific comparison is
intentional and captioned. But the same chart's **FY2024 (green) line is
provided as a comparison year and is drawn essentially flat at ~$0 for the
entire fiscal year (Oct through early Sept), then jumps almost vertically
to its final value of $7.250B in the very last days of the fiscal year.**
A reader who takes the green line at face value for any month before
September would conclude NOAA ORF obligated almost nothing in FY2024 for
eleven months and then suddenly obligated the account's entire annual total
in days — an artifact of File B reporting lag/catch-up, not of real-world
spending timing, and nothing on the chart flags this specific year's line
as different in kind from the smoothly-accruing other years.

**(c) Claims/labels that may over-state.** The chart caption's general
hollow-point explanation does not by itself cover this case: the FY2024
line is not shown as a hollow/held-flat point (the visual convention the
page defines for "not reported"), it is shown as a normal solid line at
$0 that then rises — visually indistinguishable from "no obligations
occurred," which is very likely not what happened.

**(d) Specific text checks.** "Award-level detail is sparse" — not present
(this note is DOD-specific; NOAA's File C share is high). "Award ledger:" /
"Obligations from" — not on this page. "Not reported at pull" — present,
verbatim, in the standard caption. "Counts as of the pull date" — not
found. Hollow/open circle markers — present and visible on the FY2025
(red-orange) line around Nov–Feb, consistent with the caption.

**(e) Chart/table anomalies — HIGH SEVERITY.** In addition to the FY2024
near-zero-then-vertical-jump pattern described in (b)/(c) above, the
FY2023 (gold) line shows a visible **~$1.1B dip** around May–June (from
roughly $5.7B down to roughly $4.6B) before recovering and continuing to
climb — a mid-year partial collapse in a cumulative series that, by the
page's own "negative activity stays negative" rule, should only be
possible if a downward correction (de-obligation/reconciliation) exceeded
new obligations in that window. This is plausible per the page's stated
methodology but is not called out inline, and combined with the FY2024
near-total-reporting-lag pattern, this page has the most reporting-lag /
correction-driven volatility of any account reviewed.

---

## 7. obligations-account-commerce-nist-its.png — NIST Industrial Technology Services

**(a) First-time-visitor takeaway.** NIST ITS obligated $1.011B in FY2026
to date across a small number of program activities (CHIPS $900M being the
dominant one), with a recipient table and gross-flows table populated by
manufacturing-extension-partnership grantees.

**(b) Most misleading possible reading.** The "Cumulative net obligations"
chart, read at any point between roughly January and August, would lead a
reader to believe **FY2025 obligations for this account reached
approximately $6 billion** — the orange FY2025 line jumps almost vertically
from near $0 to $6B in December/January and is held flat at that level for
eight months. The chart's own end-of-year legend, however, reports
**FY2025 · $719M** — meaning the value shown on-screen for most of the
year was roughly **8x** the account's actual final FY2025 total.

**(c) Claims/labels that may over-state — HIGH SEVERITY, exact evidence.**
No text label makes this claim explicitly, but the **chart form itself**
does: for eight of twelve months the plotted FY2025 line sits at ~$6B, a
value never realized in any reported total for this account (FY26 · $1.011B,
FY25 · $719M, FY24 · $440M, FY23 · $213M, FY22 · $238M are all the
labeled endpoints, none near $6B). This is the single most misleading
individual chart element found across all ten pages reviewed: it is not a
rendering glitch visible only on close inspection — it is a full-height,
multi-month plateau at 5-8x the scale of every other line on the same
axes.

**(d) Specific text checks.** "Award-level detail is sparse" — not present
(NIST ITS is not a DOD account). "Award ledger:" / "Obligations from" —
not on this page. "Not reported at pull" — present, verbatim, standard
caption. "Counts as of the pull date" — not found. Hollow/open marker —
none clearly visible distinguishing the $6B plateau from a normal reported
value; the plateau is drawn as a solid (not hollow) line, meaning the page's
own visual convention marks it as an *actually reported* File B value, not
a "held over from last report" placeholder — which makes the eventual
$719M endpoint even harder to reconcile without assuming a large downward
correction occurred right at fiscal year-end.

**(e) Chart/table anomalies.** The companion "Obligations by reporting
period" chart for this same account shows a period spike to roughly +$60M
around 2025P04 and a dip to roughly -$40M around 2025P09 — consistent with
a big one-off entry and its later reversal, and directly corroborating the
cumulative-chart spike/collapse described above.

---

## 8. obligations-account-doe-sc.png — DOE Office of Science

**(a) First-time-visitor takeaway.** DOE SC obligated $7.717B in FY2026 to
date across well-known national-lab program activities (Basic Energy
Sciences $2.075B, High Energy Physics $977M, etc.), with the highest File C
linkage of any page reviewed (90.7%), and a recipient table topped by
UT-Battelle LLC ($1.275B).

**(b) Most misleading possible reading.** None significant found — the
cumulative-by-year chart shows smooth, closely-spaced step lines for all
five years (FY22–26) without any dramatic spikes or collapses, the
per-period chart shows normal noisy variation in the $0–$30M range, and the
File C/net ratios in the program-activity table are all in a plausible
60–100% band. This is the "clean" comparison page among those reviewed. If
anything, a reader unfamiliar with GTAS reconciliation could over-trust the
$6.999B "File C portion (90.7% of net)" figure as meaning "we have complete
award data for 91% of this account," when the page's own footnote clarifies
File C/net is a signed ratio, not a completeness score.

**(c) Claims/labels that may over-state.** The footnote itself
pre-empts this ("File C / net is a signed ratio, not a completeness score;
at Program Activity level it can fall outside 0–100% when File C and the
residual offset"), so no label here actually oversells the number, but nothing
above the fold restates that caveat next to the "90.7% of net" headline
figure itself.

**(d) Specific text checks.** "Award-level detail is sparse" — not present
(DOE SC is not the DOD note). "Award ledger:" / "Obligations from" — not on
this page. "Not reported at pull" — present, verbatim, standard caption.
"Counts as of the pull date" — not found. Hollow/open marker — none clearly
visible in this account's cumulative chart; all five lines appear as solid,
closely-tracking steps.

**(e) Chart/table anomalies.** None found. This page is the strongest
positive control among the ten: chart shapes, table contents, and headline
figures are mutually consistent.

---

## 9. obligations-account-dhs-cisa-rd.png — DHS CISA R&D

**(a) First-time-visitor takeaway.** CISA R&D obligated $792K in FY2026 to
date (through only 20 distinct linked awards total across all years),
overwhelmingly attributed to a single program activity ("CAS -
Infrastructure Security R&D"), with essentially every other program
activity and recipient/flow table empty.

**(b) Most misleading possible reading.** The "Net obligations by fiscal
year" bar chart shows a decline from roughly $16M (FY19) to a essentially
flat, near-zero bar for FY25 ($98) and a small FY26 bar ($792K) — a >99.99%
apparent decline that a reader could cite as "CISA R&D funding was
effectively eliminated," without any inline text explaining whether that
reflects a real program wind-down, a reclassification to a different
account/program activity, or a reporting change. The page provides no
narrative for this specific trend (unlike the general DOD note, which
does not apply here since DHS is not flagged with that caveat).

**(c) Claims/labels that may over-state.** None literally false; the
absence of explanation for the apparent funding cliff is the issue, not a
false claim.

**(d) Specific text checks.** "Award-level detail is sparse" — not
present (no DOD-style note for DHS). "Award ledger:" / "Obligations from" —
not on this page. "Not reported at pull" — present, verbatim, standard
caption. "Counts as of the pull date" — not found. Hollow/open marker —
none clearly visible (the account is small enough that most of the
cumulative-chart lines sit near the bottom of the chart with limited visual
resolution).

**(e) Chart/table anomalies.** The "Obligations by reporting period" chart
shows a sharp dip to roughly -$14M immediately followed by a rise to
roughly +$14M around January 2023 — a clean negative-then-positive pair of
comparable magnitude to the account's entire multi-year total, again with
no inline annotation. Given how small this account now is, this single
one-off swing from FY23 dominates the visual scale of the whole chart,
which somewhat exaggerates how volatile the account currently is (FY25/FY26
bars are near-zero and unaffected by that swing).

---

## 10. sentinel.png — "Funding-action sentinel"

**(a) First-time-visitor takeaway.** This page tracks 176 "episodes" of
detected negative or unusual financial activity (400 underlying financial
observations) across the same registered obligation accounts, cross-referenced
against two authoritative sources (a DOE termination announcement and an
NSF terminated-awards list). Only 2 of 176 episodes have a source-confirmed
status event; 174 are "unreviewed signals," and the page repeatedly states
that a signal is not itself a cancellation.

**(b) Most misleading possible reading.** A reader skimming episode
titles and negative dollar figures (e.g., "National Marine Fisheries
Service -$526M gross negative", "Weapons Activities (Direct) -$1.004B
gross negative") without reading the per-episode explanatory line
("Gross negative File C activity triggered a mechanical rule. The sign and
amount do not establish a cancellation.") could read this page as a list of
176 confirmed funding cuts or terminations, when the page's own top banner
states the opposite: **"A signal is not a cancellation. A financial
observation is not a confirmed cancellation. Confirmation requires an
accepted authoritative sourced status event."**

**(c) Claims/labels that may over-state.** The "unreviewed for N days"
phrasing (up to **"unreviewed for 294 days"**) sits next to episode titles
in exactly the same visual weight as the dollar figures, despite the page
itself stating "an unreviewed state is durable and has no deadline" — see
(d) below for the specific gap this creates.

**(d) Specific text checks (verbatim, as requested).**
- "Award-level detail is sparse" — not present on this page.
- "Award ledger:" — not present on this page.
- "Obligations from" — not present on this page.
- "not reported at pull" — not present on this page.
- "net activity in this period was positive" — **present**, verbatim, on
  the "Weapons Activities (Direct)" episode: **"State: net activity in
  this period was positive."** (net activity +$1.981B despite -$1.004B
  gross negative — i.e., the negative entries were more than offset by
  positive entries in the same window, and the page flags this explicitly.)
- "award IDs with negative entries" — **present**, verbatim, on essentially
  every episode card, e.g. **"1,317 award IDs with negative entries"**
  (National Ocean Service), **"305 award IDs with negative entries"**
  (Science (Direct)).
- absence of "(not overdue)" — **confirmed absent**. Despite multiple
  episodes carrying day-counts as high as "unreviewed for 294 days" (National
  Ocean Service, Oceanic and Atmospheric Research, National Marine
  Fisheries Service, National Weather Service, 2022 Supplemental, National
  Environmental Satellite Service) directly under a page-level statement
  that "an unreviewed state is durable and has no deadline," no episode
  card anywhere on the page carries a "(not overdue)" or equivalent
  qualifier next to its day-count. The day-count styling (bold number +
  "days") reads exactly like an SLA/backlog metric even though the page's
  own design intent is that no deadline exists.
- Final card and notes/limits section — **fully rendered, no clipping**.
  The page ends cleanly with "Show 154 more unreviewed episodes," then a
  complete "Coverage and interpretation limits" bulleted list (8 items:
  Incomplete discovery, No motive inference, No legal judgment, Amounts are
  not interchangeable, Award mapping can be partial, Routine versus
  extraordinary remains unresolved, No comprehensive real-time docket
  monitoring, Sources are attributed not independently proven, Review is
  optional judgment), followed by a complete "Estimated pilot burden" table
  (5 rows) and a closing line: "These are planning ranges. Replace them
  with measured figures after eight weeks without delaying publication,
  account fan-out, or closing this implementation phase." No blank tail or
  cut-off text was found.

**(e) Chart/table anomalies.** This page has no charts, only text/number
cards, so the "cumulative line" and "period chart" checks in item (e) do
not apply. One structural note: two separate episode cards share the exact
same title with different numbers and windows — **"Advanced Industrial
Facilities Deployment Program"** appears twice (**-$95.0M / -$95.0M net**,
observed 2026-07-31; and **-$74.9M / -$74.9M net**, observed 2026-04-30;
and a third, **-$51.0M / -$51.0M net**, observed 2026-03-31) and
**"National Environmental Satellite Service"** appears twice (**-$323M /
-$309M net**, observed 2025-11-30 through 2026-07-31; and **-$85.4M /
-$83.4M net**, observed 2025-11-30 through 2026-04-30). Because the cards
are not visually grouped or cross-referenced, a reader skimming totals
could double-count the same underlying program's negative activity as three
(or two) independent, additive events rather than overlapping/successive
observation windows on what may be the same program.

---

## Ranked cross-page findings

| # | Severity | Finding | Page(s) | Exact evidence |
|---|----------|---------|---------|----------------|
| 1 | **High** | Cumulative-obligations chart plots a full fiscal year at ~8x its actual year-end total for 8 of 12 months, with no annotation distinguishing it from a normal reported value. | `obligations-account-commerce-nist-its.png` | FY2025 (orange) line plateaus at ~$6B from Dec/Jan through Aug; legend endpoint reads "FY25 · $719M". |
| 2 | **High** | Cumulative-obligations chart shows a ~$17-20B mid-year spike (to ~$46B) that later collapses back to the reported year-end total, unexplained by the page's own "hollow point" convention (which is used elsewhere on the same chart for a different line). | `obligations-account-dod-navy-rdte.png` | Green FY2024 line plateaus near $46B in Aug, drops to labeled endpoint "FY24 · $29.563B"; hollow marker instead appears on the gold FY2023 line. |
| 3 | **High** | A comparison year's cumulative line sits at ~$0 for essentially the entire fiscal year, then jumps almost vertically to its full annual total in the final days — visually indistinguishable from "no funding occurred until year-end," which is very unlikely to be literally true. | `obligations-account-commerce-noaa-orf.png` | FY2024 (green) line flat near $0 through ~Aug, vertical rise to labeled endpoint "FY24 · $7.250B" at the Sep edge; not marked as a hollow/held-over point. |
| 4 | **Med** | Page states unreviewed episodes are durable with "no deadline," yet every episode card displays a bolded day-count ("unreviewed for 294 days") with no "(not overdue)" or equivalent qualifier, inviting a backlog/SLA reading the page's own text disclaims. | `sentinel.png` | "An unreviewed state is durable and has no deadline" (page banner) vs. "Observed 2025-11-30 through 2026-07-31 · unreviewed for 294 days" (multiple episode cards); no "(not overdue)" found anywhere on the page. |
| 5 | **Med** | For DOD accounts with 0.0% File C linkage, the "Top recipients" and "Largest award-attributed gross flows" sections render with only a "Show N more rows" toggle and no visible content or explanatory placeholder, which can read as missing/broken data rather than "not published for this line" (a distinction only explained in a note higher on the page). | `obligations-pa-dod-basic-research.png`, `obligations-account-dhs-cisa-rd.png` (partial) | "File C portion, FY2026 to date (0.0% of net) $0" / "Distinct File C-linked awards … 0" with empty recipient/flow sections below. |
| 6 | **Med** | A single one-off large negative-then-positive swing in a period-level chart can dominate the visual scale of an entire multi-year chart for a now-small account, exaggerating apparent current-year volatility. | `obligations-account-dhs-cisa-rd.png` | "Obligations by reporting period" dips to ~-$14M then rises to ~+$14M around Jan 2023, on a chart whose FY25/FY26 bars are near $0 ("$98", "$792K"). |
| 7 | **Med** | Multiple accounts' "Obligations by reporting period" charts show large single-period negative/positive pairs with no inline annotation calling out the specific periods as one-off corrections (the page only explains the general mechanism in a footnote). | `obligations-account-dod-navy-rdte.png`, `obligations-pa-dod-basic-research.png`, `obligations-account-commerce-noaa-orf.png` | Navy: dip to ~-$120M / spike to ~+$150M; Army Basic Research: dip to ~-$20-30M / spike to ~+$130M (mid-2025); NOAA ORF: dip/spike of ~$40-60M (late 2023). |
| 8 | **Low** | Two program/unit titles each appear as multiple separate, unlinked episode cards with different dollar figures and overlapping observation windows, risking double-counting by a reader who sums visible totals. | `sentinel.png` | Two "Advanced Industrial Facilities Deployment Program" cards (-$95.0M and -$74.9M, plus a third at -$51.0M) and two "National Environmental Satellite Service" cards (-$323M and -$85.4M). |
| 9 | **Low** | A steep, unexplained apparent decline in a small account's annual totals (FY19 ~$16M to FY25 $98 to FY26 $792K) has no narrative note addressing whether this is real, a reclassification, or a reporting artifact. | `obligations-account-dhs-cisa-rd.png` | Net-obligations-by-fiscal-year bars: '19 tallest (~$16M), '25 near-zero, '26 $792K, with no explanatory text. |
| 10 | **Low** | The landing page places an all-time cumulative total ($2703.529B) directly above a single-fiscal-year total ($285.826B) with similar visual weight, risking conflation of the two. | `obligations-landing.png` | "$2703.529B net obligations across 502,001 distinct linked awards … Net obligations, FY2026 to date $285.826B" appear within a few lines of each other. |
| 11 | **Low** | Requested phrase "counts as of the pull date" was checked for and not found on any of the ten reviewed pages. | all | Not found (documented for completeness, not itself a defect). |
