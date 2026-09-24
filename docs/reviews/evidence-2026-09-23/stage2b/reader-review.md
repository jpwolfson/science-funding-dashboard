# Reader review — Federal science funding dashboard

## Reviewer context

I reviewed 74 full-page PNG screenshots (1100px wide, light mode) supplied in
`pack/`. I had no access to repository files, source code, documentation, or
prior reviews — only the rendered pages themselves. Tall pages were cropped
into overlapping ~1100×1400 strips (Pillow) and read as an ordinary visitor
would scroll them; shorter pages were read as single downsized images.

**Read in full, top to bottom:** `award-root`, `award-nih`, `award-nsf`,
`obligations-landing`, `sentinel`, `obligations-account-dod-army-rdte`,
`obligations-account-usda-nifa-research-education`,
`obligations-account-commerce-noaa-orf`, `obligations-account-dod-navy-rdte`,
`obligations-account-doe-sc`, `obligations-account-nasa-science`,
`obligations-account-dhs-cisa-rd`.

**Skimmed for anomalies (all 62 remaining pages):** every other
`obligations-account-*` page (DOE, DOD, NASA, USDA, Commerce, DHS, DOT, ED,
EPA, HHS, VA, NSF sub-accounts), every `obligations-pa-*` "unknown/other" and
named program-activity page, and the NIH Clinical Center / NSF BFA
sub-directorate award pages. I did not view every table row hidden behind
"show N more" disclosures on skimmed pages.

I read as a policy staffer or journalist would: taking headline numbers,
chart annotations, and quoted source text at face value, and asking what a
first-time visitor with no methodology background would walk away believing.
All quotations below are transcribed exactly as rendered.

---

## 1–3. What a visitor would conclude / most misleading reading / unsupported implications, by page

### `award-root` — "Federal science funding dashboard"
**Conclusion a visitor would draw:** NIH and NSF combined made 863,106 awards
since Oct 2014; FY2026 (Oct–Jul) activity is running noticeably behind
history — awards down **−18.3%**, new/standard awards down **−27.1%**,
continuing awards down **−11.1%**, dollars roughly flat (−0.9%) — with NSF's
own row showing new awards down **−46.3%** vs the FY15–24 average.

**Most misleading reading:** That FY2026 activity is down ~18–46% because of
an ongoing, uniform funding cut across the government. In fact the
comparison window (Oct–Jul) includes the **October 1 – November 11, 2025
government shutdown**, which the page discloses only in chart captions
further down the page ("October 1 – November 11, 2025 was a lapse in federal
appropriations; award counts in those months are low"), not next to the
top-line stat tiles or the NSF/NIH agency table where the percentages
actually live. A visitor who reads only the top of the page — the part most
people read — sees four red percentages with no shutdown context at all.

**Unsupported implication:** The red "vs FY15-24 avg" tiles and table cells
present a single ten-year average as the implicit "normal" baseline with no
trend line, no confidence band, and no adjacent caveat about the shutdown or
about agency-specific mechanism changes (both of which are explained later,
in "How to read this," but not at the point of comparison). The visual
design (red, minus sign, prominent placement) reads as "funding is being
cut" more than the underlying data supports on its own.

### `award-nih`
Straightforward FY-to-date and historical award/dollar dashboards for NIH.
Caveats about revised notice dates and outlier awards are present and
adequate. No misleading chart forms or unsupported juxtapositions found on
this page.

### `award-nsf`
**Conclusion a visitor would draw:** NSF award activity has fallen sharply in
FY2026, and the decline is wildly uneven by directorate: SBE (Social,
Behavioral and Economic Sciences) is down **−85.2%**, EDU (STEM Education)
down **−70.3%**, OD (Office of the Director) down **−59.4%**, TIP down
**−50.8%**, GEO down **−50.5%**, and BFA/IRM (administrative offices) down
**−100.0%** (literally zero new awards).

**Most misleading reading:** That NSF as a whole, or specific directorates
such as SBE, have been formally "cut" by the percentages shown. The page
never asserts this, and to its credit does not name a cause — but a table of
double-digit and triple-digit negative percentages sitting next to no
methodological caveat (the shutdown note is three sections below, in a chart
caption) invites readers to treat the percentage as a funding-cut figure
rather than an award-count artifact of a partial fiscal year plus a
six-week lapse in appropriations.

**Unsupported implication:** None beyond what's noted above — the
directorate table itself is presented neutrally (no color commentary, no
editorializing text), but the magnitude and specificity of the SBE/EDU
figures make them the kind of number a reporter would lift out of context.

### `award-nih-cc` / `award-nsf-bfa` / `award-nsf-bfa-bfa` (skim)
These leaf pages for non-awarding administrative units (NIH Clinical Center,
NSF Office of Budget/Finance) correctly show "$0 / baseline n/a" and explain
that the unit doesn't make competitive awards. No issues. One general
pattern surfaces here: units with a handful of awards in only one baseline
year display **−100.0%** even though the "baseline" was itself tiny (e.g. 12
awards in FY22 and zero every other year) — this is covered in the
cross-page findings table below.

### `obligations-landing`
Careful, technical framing: obligations are explicitly distinguished from
appropriations/outlays, File B vs. File C vs. residual are defined up front,
and the page states plainly that account-level obligations are "not
directly comparable" to the award ledger. No misleading juxtapositions
found. This is one of the better-hedged pages on the site.

### `obligations-account-dod-army-rdte`
Standard obligation-ledger layout with the DOD-wide "Interpretation note"
explaining that low File C award-linkage is a data-attribution limit, not
evidence of missing dollars. Well hedged. One recipient's award title is
literally the string `"RESERVED"` — a source-data artifact, not a dashboard
error, but potentially confusing without a footnote.

### `obligations-account-usda-nifa-research-education`
**Conclusion a visitor would draw:** Standard obligation ledger for
NIFA Research & Education.

**Most misleading / most notable:** Several of the largest negative
("de-obligation") flow-table entries for FY2026 show the *award title* field
as verbatim government text:
> **"** AWARDS ISSUED PRIOR TO JANUARY 20, 2025, WERE FUNDED UNDER PREVIOUS ADMINISTRATIONS AND MAY NOT REFLECT THE PRIORITIES AND POLICIES OF T…"**
This appears at least four times in the visible top-10 flow rows alone
(North Carolina State −$721K, North Dakota State −$676K, Virginia Tech
−$644K, Utah State −$1.5M), and the identical phrase recurs in the sibling
`obligations-account-usda-nifa-extension` page's flow table too. It is
correctly quoted and labeled "source description," so the site is not
inventing or editorializing this language — it is the federal government's
own award-record text. But it sits in a plain data table with no narrative
treatment, no link to the funding-action sentinel, and no callout, even
though it is arguably the single most directly "motive-bearing" piece of
text anywhere on the site (more explicit than anything on the sentinel
page). A reader who does not already know the site's sentinel/episode
methodology could easily miss that this is exactly the kind of signal the
sentinel page says it curates carefully — it is not curated here at all.

### `obligations-account-commerce-noaa-orf`
Standard layout. Several Program Activities show extreme File C/net
percentages (NESDIS −202.9%, Spectrum Relocation Fund −298.0%) which are
mathematically correct but visually alarming without a plain-English gloss
next to the number (the generic explanation is in the section header, not
attached to the specific outlier row).

### `obligations-account-dod-navy-rdte`
Standard, well-hedged DOD interpretation note present. No new issues.

### `obligations-account-doe-sc` (Office of Science)
Standard layout; FY2026-to-date cumulative line runs meaningfully below
FY2022–25 at the same point in the year. No annotation explains why (no
shutdown/appropriations note appears on obligation-ledger pages the way it
does on award pages) — a reader comparing this page to the award pages
might wonder why one set of charts flags the shutdown and the other doesn't.

### `obligations-account-nasa-science`
Standard layout, well hedged. Notable only in combination with the sentinel
page's "Science (Direct) · NASA Science" entry (see below) — a reader
following a sentinel link here sees a fully ordinary, un-annotated ledger
page with no back-reference to the sentinel episode, so context is easy to
lose in either direction.

### `obligations-account-dhs-cisa-rd`
**Conclusion a visitor would draw:** CISA's cybersecurity R&D obligations
fell from **$6.8M (FY22)** and **$9.8M (FY23)** to essentially **$98 total
for all of FY2025**, before ticking back up to $792K in FY2026 to date. The
"Net obligations by fiscal year" bar for FY25 is visually almost invisible.

**Mitigation already in place:** the page includes an explicit "Notes on
source figures" box stating: *"FY2025, period 12: The source reports $3.31
million for this account in FY2024 and $98 in FY2025. Source figures alone
do not show whether the activity ended or moved to another account."* This
is a good, honest disclosure.

**Residual risk:** the disclosure is text below the chart, not on the chart
itself. A visitor who screenshots or skims just the fiscal-year bar chart
(a plausible, shareable image — "CISA cybersecurity R&D funding effectively
zeroed out in FY2025") would carry away a stronger claim than the page
itself is willing to make.

### `sentinel` (Funding-action sentinel) — read in full
**Conclusion a visitor would draw:** The site tracks 176 "episodes" of
negative financial activity across federal science accounts; 174 are
"Unreviewed signals" and 2 are "Source-confirmed." The two confirmed
episodes are DOE's October 2025 termination announcement (quoted headline:
*"Energy Department Announces Termination of 223 Projects, Saving Over $7.5
Billion,"* announced affected value *"approximately $7.56 billion"*) and an
NSF terminated-awards list (1,667 award IDs, dated June 5, 2025).

**What's done well:** Every single episode entry — without exception in the
sections I read — repeats some version of *"Gross negative File C activity
triggered a mechanical rule. The sign and amount do not establish a
cancellation."* The DOE episode explicitly separates the announcement from
"any later appeal, closeout, litigation, deobligation, or restoration,"
labels the stated reason as *"(paraphrase, not verbatim)"*, and states
*"the announcement did not publish award identifiers; no award-level match
is inferred."* This is genuinely careful, well-lawyered writing that
actively works against the misleading reading a reader might bring to the
page.

**Most misleading reading:** Despite the careful per-episode language, nine
DOE File C observations and this repeated-warning structure are visually
identical in format to 174 *other*, un-vetted "unreviewed" episodes with no
confirming source at all — some individually larger in dollar terms than
the confirmed DOE episode. E.g., **"National Ocean Service · NOAA ORF ·
FY2026 −$484M File C gross negative · −$470M File C net activity"** with
**"1,317 award IDs with negative entries"** — nearly five times DOE's
confirmed $95M single-observation figure and four times its award count —
sits a few screens below the confirmed episodes with only the same
one-line disclaimer and no news hook. A skimming reader (or one who
screenshots a section) could easily treat "Unreviewed signal" episodes as
equivalent in evidentiary weight to the confirmed ones, especially since the
page's own headline stat — "174 Unreviewed signals" vs. "2 Source-confirmed"
— invites a reader to wonder what happened in the other 174, without any
per-episode indication of which ones are payroll/timing noise vs.
something newsworthy.

**Unsupported implication check:** I found no instance where the sentinel
page itself asserts a cause, names a motive, or claims a cancellation
without the disclaimer attached. The risk here is entirely about *scale and
placement* (174 identically-formatted alarming dollar figures against a
backdrop of only 2 confirmed episodes), not wording.

### Skimmed `obligations-account-*` and `obligations-pa-*` pages (62 pages)
The vast majority are structurally identical to the pages read in full and
carry the same generic caveats. Notable outliers found while skimming:

- **`obligations-account-doe-oced`** (Clean Energy Demonstrations — the
  office named in DOE's October 2025 termination announcement): "File C
  portion, FY2026 to date **(−3881.2% of net)**" against a $15.7M net
  figure — the most extreme File C/net ratio found anywhere on the site.
  Given OCED is the flagship agency in the sentinel's one confirmed
  termination story, this page is likely to be read immediately after or
  alongside the sentinel entry, and the extreme, unexplained percentage
  could reinforce (accurately or not) a "this office is being unwound"
  narrative without the page itself making that connection or hedging it
  the way the sentinel page does.
- **`obligations-pa-nsf-unknown-other`**: "File C is award-financial
  enrichment. Across the full displayed history, File C / net is
  **100167255.7%**." On a $25K account. This is not merely a large
  percentage like the ones elsewhere — it is over 100 million percent, and
  reads like a display bug rather than a legitimate signed ratio, which
  risks undermining a reader's trust in every other number on the site
  even though the underlying math (tiny denominator, unrelated numerator)
  is internally consistent with the disclosed methodology.
- **`obligations-account-va-medical-prosthetic-research`**: **0.0% File C
  linkage across the entire $8.8B, 10-year history** — every single dollar
  is unlinked to award-level detail. Unlike DOD accounts (which display an
  explicit "Interpretation note" explaining sparse File C linkage is
  normal for their agency), the VA page carries no such note anywhere,
  despite having the most extreme case of missing award-level linkage of
  any page reviewed.
- Several accounts (`doe-fossil-energy`, `commerce-noaa-pac`,
  `usda-nifa-extension`, `dod-navy-rdte` "Undistributed" line, etc.) show
  isolated extreme File C/net percentages (from −298% to −28,409.5%) driven
  by tiny-denominator arithmetic — a systemic pattern rather than isolated
  errors (see finding #4 below).
- The recurring "*** AWARDS ISSUED PRIOR TO JANUARY 20, 2025 …" quoted
  disclaimer text also appears in `obligations-account-usda-nifa-extension`'s
  flow table, confirming this is a widespread, not one-off, government
  source-data pattern.

---

## Ranked cross-page findings

| # | Severity | Finding | Page(s) | Exact evidence (quoted) | Suggested fix |
|---|----------|---------|---------|--------------------------|----------------|
| 1 | **High** | Top-line "vs FY15-24 avg" decline percentages (site-wide and per-agency) are shown in red with no adjacent context about the Oct 1–Nov 11, 2025 appropriations lapse that falls inside the comparison window, or about the partial-year nature of the comparison. The shutdown caveat exists but is several screens below, in chart captions. | `award-root`, `award-nsf` | "Awards, FY2026 Oct–Jul: 44,845 · **−18.3%** vs FY15-24 avg"; "New/standard awards, Oct–Jul: 13,212 · **−27.1%**"; NSF row: "4,570 · **−46.3%**"; shutdown note ("October 1 – November 11, 2025 was a lapse in federal appropriations; award counts in those months are low.") appears only in a chart caption further down | Put a one-line shutdown/partial-year caveat directly beside every red percentage tile and every "vs FY15-24 avg" table column, not only in chart captions |
| 2 | **High** | A negative File C flow row's *award title* field is verbatim government text stating pre-2025 awards "may not reflect the priorities and policies" of the current administration — the most directly motive-adjacent language on the entire site — yet it appears in a plain, uncurated obligation-ledger table with no sentinel linkage, no episode treatment, and no disclaimer, unlike DOE's comparable negative-activity narrative on the sentinel page. | `obligations-account-usda-nifa-research-education`, `obligations-account-usda-nifa-extension` | *"** AWARDS ISSUED PRIOR TO JANUARY 20, 2025, WERE FUNDED UNDER PREVIOUS ADMINISTRATIONS AND MAY NOT REFLECT THE PRIORITIES AND POLICIES OF T…"* (repeated for North Carolina State −$721K, North Dakota State −$676K, Virginia Tech −$644K, Utah State −$1.5M, all FY2026P06–P09, "Negative entry") | Route award titles matching this or similar government disclaimer patterns into the sentinel's episode/disclaimer treatment, or at minimum add a footnote where this text appears in obligation-ledger flow tables |
| 3 | **Medium** | The sentinel page presents 174 "Unreviewed" episodes in the identical visual/textual format as its 2 "Source-confirmed" episodes, including at least one unreviewed episode (NOAA ORF) far larger in dollars and award count than the confirmed DOE episode. This risks readers treating unreviewed and confirmed signals as equally evidentiary. | `sentinel` | "National Ocean Service · NOAA ORF · FY2026 **−$484M** File C gross negative · **−$470M** File C net activity (observation window) … **1,317 award IDs with negative entries**" vs. confirmed DOE episode's "**−$95.0M**" / "1 award IDs with negative entries" (OCED) or "321 awards · 223 projects" (DOE announcement) | Visually distinguish unreviewed volume/scale from confirmed episodes (e.g., collapse large unreviewed episodes by default, or add a "not yet checked against any news source" badge distinct from the existing disclaimer sentence) |
| 4 | **Medium** | A recurring pattern across dozens of obligation-ledger pages: File C/net percentages on small-denominator Program Activities produce extreme, alarming-looking figures (down to millions of percent) that are mathematically valid under the disclosed "signed ratio" methodology but read as errors or as evidence of dramatic funding swings. | Many `obligations-account-*` and `obligations-pa-*` pages | `obligations-pa-nsf-unknown-other`: "File C / net is **100167255.7%**" on a $25K account; `obligations-account-doe-oced`: "File C portion, FY2026 to date (**−3881.2%** of net)"; `obligations-account-commerce-noaa-orf`: "NOS — National Ocean Service … **−1513.3%**"; `obligations-account-doe-fossil-energy`: "Unconventional FE Technologies … **−28409.5%**" | Suppress or visually flag (e.g., "n/m" — not meaningful) any File C/net ratio beyond a sane bound (e.g., ±300%) instead of printing the raw computed percentage |
| 5 | **Medium** | The VA Medical and Prosthetic Research account has 0.0% File C award-level linkage across its entire $8.8B, 10-year history — the most extreme case of missing award-level detail on the site — but unlike DOD accounts, it carries no "Interpretation note" explaining that this is a known agency-level limitation rather than a data gap or missing dollars. | `obligations-account-va-medical-prosthetic-research` | "File C portion, FY2026 to date (**0.0%** of net) $0"; "Top recipients of award-attributed obligations — **No File C rows linked to public awards**"; no interpretation-note box present (contrast with DOD pages' "Award-level detail is sparse for Department of Defense accounts...") | Add the same category of interpretation note used on DOD pages to VA (and any other agency) whenever File C linkage is nearly zero across the full history |
| 6 | **Low** | Several very-low-award-count directorates/divisions show "−100.0% vs FY15-24 avg" when the prior-period baseline itself was a single small non-recurring value (e.g., a handful of awards in one year, zero in all others), which reads as a full funding elimination rather than baseline noise. | `award-nsf` (BFA, IRM rows), `award-nsf-bfa-bfa` | "BFA — Office of Budget, Finance, & Award Management … 0 · **−100.0%** · $0K"; "IRM — Office of Information & Resource Management … 0 · **−100.0%**" | Show "n/a (baseline < N awards)" instead of −100.0% when the historical baseline itself is below a minimum-count threshold |
| 7 | **Low** | DHS CISA R&D's FY2025 fiscal-year bar is visually near-invisible ($98 total obligated for the full year) with the explanatory note placed in a text box below the chart rather than on the chart itself, so a cropped/shared image of the chart alone would overstate the finding beyond what the page's own text supports. | `obligations-account-dhs-cisa-rd` | "FY2025, period 12: The source reports $3.31 million for this account in FY2024 and **$98** in FY2025. Source figures alone do not show whether the activity ended or moved to another account." | Add a short in-chart annotation (e.g., "see note") on the FY2025 bar itself, matching the "see note" convention already used elsewhere on the site's reporting-period charts |
| 8 | **Low** | Obligation-ledger pages (e.g., DOE Office of Science) show FY2026-to-date running meaningfully below prior years at the same point in the fiscal year, with no shutdown/appropriations-lapse caveat of the kind shown on award-dashboard pages, creating an inconsistency in disclosure between the two dashboard families for the same underlying period. | `obligations-account-doe-sc` and other obligation pages | Award pages: "October 1 – November 11, 2025 was a lapse in federal appropriations; award counts in those months are low." Obligation pages: no equivalent note found anywhere in the "How to read this obligation ledger" boilerplate | Add the same shutdown caveat (or an obligations-specific equivalent) to obligation-ledger pages covering the same FY2026 period |
| 9 | **Low** | A recipient award title literally rendered as the placeholder string `"RESERVED"` (source-data artifact) could be misread as a redaction or a site error rather than an unremarkable USAspending field value. | `obligations-account-dod-army-rdte` | Award title: `"RESERVED"`, Recipient: Lockheed Martin, −$46.5M | Add a footnote/tooltip when the raw award title equals a known placeholder value like "RESERVED" |

### Severity counts
- **High:** 2
- **Medium:** 3
- **Low:** 4
- **Total findings:** 9

### High findings, one line each
1. Site-wide and NSF decline percentages ("−18.3%", "−27.1%", "−46.3%" vs. FY15-24 avg) are shown in red with the government-shutdown context buried in chart captions rather than beside the numbers, inviting a "funding cut" reading of what may be substantially a shutdown/partial-year artifact.
2. USDA NIFA obligation-ledger flow tables surface literal government text ("awards issued prior to January 20, 2025 … may not reflect the priorities and policies") on negative entries with no sentinel-style disclaimer or curation, unlike the careful treatment given to DOE's comparable episode on the sentinel page.

---
## Coordinator dispositions (2026-09-24)

Reviewed pack: the screens tier on `3bc91f2d` (all Stage 2b items; registry
382/382, fast 7/7, rendered 4/4, screens 74). **Gate:** no High was introduced
by Stage 2b (both were live on `main` before it; Stage 2 review H7 and M8), so
neither blocks release under rule 5. H1 is fixed anyway.

| # | Sev. | Disposition |
|---|---|---|
| 1 | High | Pre-existing (Stage 2 M8; the tiles and their deltas predate Stage 2b). **Fixed:** the owner-approved item-19 sentence now also sits directly under the FY2026 headline tiles on every award page (`tileLapseNote`), not only in chart captions. The suggested "partial-year" caveat is already carried by the tile labels ("Oct–Jul"); no new wording. |
| 2 | High | Pre-existing (Stage 2 H7). Item 18 is working as approved: the reviewer confirms the text is "correctly quoted and labeled 'source description'". The remaining ask (sentinel routing or a footnote about this text) is editorial/public-claim framing (layer b). **Routed to the owner** as a follow-up option memo; not a Stage 2b gate. |
| 3 | Med | Pre-existing (Stage 2 L19 family; the unreviewed/confirmed state badges and "Episode status" note are the owner-approved design). Recorded. |
| 4 | Med | Pre-existing (Stage 2 M15, disclosed signed-ratio note). Recorded for a later batch. |
| 5 | Med | Pre-existing (Stage 2 L25). Registry `interpretationNote` is 3.2e's file; recorded for a later batch. |
| 6 | Low | Pre-existing (Stage 2 M10). Recorded. |
| 7 | Low | Pre-existing (Stage 2 item 8 design; the period chart carries "see note"). Recorded. |
| 8 | Low | Not adopted: the approved sentence is about award counts; an obligations equivalent would be new wording (owner layer). Recorded. |
| 9 | Low | "RESERVED" is now quoted and marked "source description" by item 18, which is the approved treatment of source text. No change. |
