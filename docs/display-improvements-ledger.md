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
