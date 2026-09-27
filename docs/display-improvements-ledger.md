# Display-improvements ledger

Owner-created 2026-08-14. A queue of visual/presentation improvements to
execute as one batch AFTER Phase 3.2d completes and its site-wide reader
review lands. Rules: items here are display-level only (no data or store
semantics changes); the batch runs under the working regime's reader-review
gate; every item must preserve the site's honesty-about-granularity and
attributed-language principles — an improvement that smooths, interpolates,
or fabricates precision is disqualified by definition. Add items with a
date, origin, and rationale; do not execute piecemeal while 3.2d workers
are in flight (site/** is contract-forbidden to them, and batching keeps
the reader review meaningful).

## Queued items

1. **Obligation period charts: explicit step rendering + cadence caption**
   (2026-08-14, owner request). Obligation series are reported in monthly
   agency submission periods (P02 spans Oct+Nov; early years quarterly-era),
   so the charts move in stairs while award-ledger charts move daily —
   correct, but unexplained, and readers contrast the two. Lean INTO the
   granularity rather than away from it: render period series as explicit
   step charts, and add one caption line — "obligations are reported in
   monthly agency submission periods; steps reflect reporting cadence, not
   action dates." Do NOT smooth or interpolate; the step shape is the data
   telling the truth about its resolution (docs/obligation-ledger.md:
   "never invents action-month precision"). The failure mode this item
   guards against is real and common in public spending dashboards:
   sloped lines drawn between submission periods depict intra-month
   timing that DATA Act files do not contain.

2. **Metric-identity audit across all tabs and charts** (2026-08-14,
   inspired by the sciencespending.org reconciliation memo). Their headline
   failure: a dollar series under a "new awards" tab, count-language in the
   chart key, metric disclosed only mid-text-box. Audit our site for the
   same class: every chart must state its metric (award count vs dollars
   vs obligations) in its title or axis — not only in a note — and must
   agree with the tab/section identity it sits under. The all-tiers
   screenshot pack (`verify.py --tier screens`) is the audit input; any
   finding is fixed in this batch and, where generalizable, added to the
   reader-review question list.

3. **Tab purity: each tab shows only the information type it claims**
   (2026-08-14, owner request). The landing page presents itself as the
   awards view but also displays obligation summary boxes (the DOE
   obligation tiles that were added below the award summary for
   discoverability). Separate cleanly: award tabs show award-ledger
   information only, obligation tabs show obligation-ledger information
   only, with cross-links for discoverability instead of mixed content.
   A tab's label is a promise about its metric; mixed boxes break that
   promise even when individually labeled — the same principle as the
   metric-identity audit, applied at page level.

4. **Empty File C sections need an inline placeholder** (2026-09-20,
   reader review `docs/reviews/evidence-2026-09-20/reader-review.md` #5).
   Accounts with 0.0 % File C linkage render "Top recipients" and gross
   flow sections with no rows and no explanation at the section; the
   sparsity note sits higher on the page. Render a one-line "no File C
   award detail reported for this account" placeholder in the empty
   section itself.

5. **Callout for correction pairs in period charts** (2026-09-20, reader
   review #6, #7). A single large negative-then-positive pair (a source
   correction) dominates a small account's whole multi-year scale and is
   explained only by a general footnote. Options for the batch: annotate
   the specific periods inline, or clip the y-axis with an explicit
   "off-scale correction" marker. Never remove the pair from the data.

6. **Sentinel episode identity and age wording** (2026-09-20, reader
   review #4, #8). Repeated identical episode titles with different
   dollar figures invite double-counting; "unreviewed for N days" reads as
   an SLA the page's own text disclaims. Sentinel-facing language: owner
   sign-off norm applies.

7. **All-time vs FY-to-date totals on the landing page** (2026-09-20,
   reader review #10). "$2703.529B net obligations" sits directly above
   "Net obligations, FY2026 to date $285.826B" with similar weight; label
   the horizon in the number's own label, not only in the caption.

8. **Small-account decline narrative** (2026-09-20, reader review #9).
   `dhs/cisa-rd` annual totals fall from ~$16M to under $1M with no
   on-page statement of whether that is real, a reclassification, or a
   reporting artifact. Data question first (registry/crosswalk check),
   then a caption if real.


9. **Staleness marker reaches the numbers, not only the name** (2026-09-23,
   W17 reader review). On award and obligation listing tables the †
   marks the unit/agency name; the numeric cells and the landing tiles
   that include a stale unit's last snapshot carry no marker, so a reader
   scanning figures can miss the disclosure. Candidate: mark the affected
   cells/tiles and point to the footnote. Applies to the W12 obligation
   pattern too; the † wording itself is owner-approved and unchanged.

10. **Raw validator warning text in the public warnings banner**
    (2026-09-23, W17 reader review). The "Data quality warnings from the
    last pull" banner renders validator strings verbatim (e.g. "invariant
    violated: award id count shrank from … to …"), which a policy reader
    can take as awards being cancelled. The instance seen was an artifact
    of the W17 acceptance branch (a deliberately rolled-back store; stores
    never shrink in production), but the banner's register is the issue:
    gloss each warning class in plain language. Public-claim wording:
    owner sign-off.

11. **Partial current month in "Awards per month"** (2026-09-23, W17
    reader review round 2; rated **High** by the reviewer, pre-existing,
    every award page). The rightmost monthly point is the still-accruing
    current month and renders as an uncaptioned cliff (DMS 6 vs a typical
    100–250; MPS 14 vs ~600), which a first-time reader can take as
    funding collapsing. Candidate: distinguish the partial month (open
    marker or "current month, partial" label). Chart geometry ⇒ rendered
    tier + before/after screenshots. Also from round 2 (Medium): on
    rollup pages the "last updated" rebuild date sits beside a child's
    "not refreshed since" date with no reconciling qualifier (fold into
    item 9; any new stamp wording is owner sign-off).

## Stage 2b queue (2026-09-23, Stage 2 release reader review)

**Owner decision, 2026-09-23 ~22:00 UTC:** "Approve all stage 2b recs,
minus the NIH obligations one we just discussed." Items 12 and 14–22 are
approved as recommended (★). Item 13 was superseded by owner option A: the
disclosure ships now (PR #94), NIH's 27 obligation accounts are onboarded as
Phase 3.2e (its own session), and 3.2e removes the disclosure.

These come from the fresh-agent reader review of the Stage 2 release pack
(`docs/reviews/evidence-2026-09-23/stage2/reader-review.md`, with the
coordinator's dispositions). Every item is pre-existing on `main`
(`c356a78`), and none blocks the Stage 2 release. Each needs an owner
decision under decision layers a/b/c, so each carries the coordinator's
recommendation (★).

12. **Obligation scope disclosure** (review H1). Registered accounts are
    included whole, so some totals also cover non-research lines: DoD
    Defense Health Program O&M, NNSA Weapons Activities, and ASPR
    procurement. ★ Append to the landing subtitle: "Accounts are included
    whole, so some totals also cover operations, procurement, or weapons
    activities alongside research." Alternatives: retitle the page; a
    research-only subtotal (a measure change, large); no change.
13. **NIH absence on the obligations tab** (H2). ★ Add "NIH accounts are
    not included here; NIH awards are on the award dashboards." to the
    landing subtitle and to the HHS row's footnote.
14. **Wording for $0 program activities** (H3). Stage 2 ships a neutral
    collapsed group. ★ No explanatory claim. The alternative is "(program
    activity codes can be retired or renamed between years)".
15. **Army RDT&E FY2022 path** (H4). The FY totals match the GTAS pins. The
    path is P06 $31.0B → P07 $74.0B → P09 $81.7B → P10 $49.9B, and no
    acceptance rule fires. ★ A CI re-pull of FY2022 P06–P10 (data session),
    then a source-figure note with owner-approved text if the re-pull
    confirms it.
16. **Source-only sentinel cards** (H5). ★ Where an episode has no linked
    ledger activity, replace "$0 gross negative · $0 net" with "no linked
    ledger activity". For source-listed IDs, replace "award IDs with
    negative entries" with "award IDs listed by the source".
17. **Sentinel "net" vs ledger "net"** (H6). ★ Label the sentinel figures
    "File C gross negative" and "File C net activity (observation
    window)".
18. **Source award descriptions shown as titles** (H7; e.g. the USDA NIFA
    "AWARDS ISSUED PRIOR TO JANUARY 20, 2025…" text). ★ Render every
    source award description in the flow tables as attributed source text,
    quoted and marked "source description", per the render-by-provenance
    rule.
19. **October–November 2025 low award counts** (M8). ★ "October 1 –
    November 12, 2025 was a lapse in federal appropriations; award counts
    in those months are low." This is an external fact stated beside the
    data, not attributed as the cause. Alternatives: a statement with no
    context; no change.
20. **Root title vs coverage** (M9). ★ Change the tile heading to "Award
    activity (NIH and NSF)".
21. **Sentinel source status and process text** (M17, M28). ★ Show source
    status as dates ("source list dated …; checked …"). Remove "Replace them
    with measured figures after eight weeks…" from the public page; it
    stays in the docs.
22. **Supplemental or one-time money** (M18). ★ No change now: any tag
    would attribute cause.
