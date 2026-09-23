# W17 reader review (2026-09-23)

Release-bar rule 5 (`CLAUDE.md`): two fresh agents with no build context
reviewed rendered screenshots only. They were asked what a first-time
visitor would conclude, what the most misleading reading is, and whether any
label or juxtaposition implies more than the data supports. Dispositions are
the coordinator's.

## Round 1: acceptance-branch pages

The pages are `nih/nci`, `nih`, the award root, and `nsf/mps/dms` (control),
rendered from branch `claude/w17-acceptance` after run 35824669422. That run
deliberately failed `nih/nci/nci` and restored its store to the refused
95,928-award state (`acceptance-nci-top.png`).

| Finding (reviewer severity) | Disposition |
|---|---|
| "Not refreshed since 2026-09-23" beside "last updated September 23, 2026"; the reader cannot tell how stale the unit is (High) | **Fixed before merge.** There were two causes. (a) With no prior entry, `staleSince` fell back to the dashboard's `generated` date, which W15's offline reaggregation had advanced. Fixed by seeding `data/refresh_status.json` with each unit's true last accepted pull (`cc89c979`). (b) A stale unit's page stamp showed the rollup rebuild date. It now shows `staleSince` on single-unit stale pages (`4f196300`). |
| "invariant violated: award id count shrank from 96436 to 95928" in the warnings banner, readable as awards being cut (High) | This is an artifact of the acceptance setup: the NCI store was rolled back on the test branch. Production stores never shrink, and a stale unit keeps its store. The underlying issue is that the banner shows raw validator text, which predates W17. Recorded as Stage 2 ledger item 10. |
| † marks names, not the figures or topline tiles that include the stale snapshot (Medium) | Same pattern as the owner-approved W12 obligation display. Recorded as ledger item 9. |
| Red year-over-year percentages with no staleness caveat (Medium) | No change. The snapshot lag is days, while the Oct–Jul window comparison is not a staleness artifact. The note's wording is owner-approved. |

## Round 2: realistic stale scenario

Scratch tree of the W17 head `4f196300`: every NSF unit pulled fresh except
`nsf/mps/dms`, stores untouched, `staleSince` 2026-09-21 from the seed.
Pages: `nsf/mps/dms`, `nsf/mps`, `nsf`, root, and `nih/nci` (control)
(`after-stale-*.png`).

The reviewer confirmed that the DMS page's stamp ("last updated September
21, 2026") and its note ("Not refreshed since 2026-09-21 …") are
consistent. The footnotes were findable and correctly scoped ("1 of 6",
"1 of 59"). The reviewer judged the wording "figures are the last accepted
snapshot" not to imply that funding stopped or that the site is broken. It
found no High issue attributable to W17.

| Finding (reviewer severity) | Disposition |
|---|---|
| "Awards per month" ends on an uncaptioned partial-month cliff (DMS 6 vs ~100–250) (High) | This predates W17 and appears on every award page, fresh or stale. Stage 2 ledger item 11, flagged to the owner as the top Stage 2 candidate. |
| Rollup "last updated" rebuild date vs a child's "not refreshed since" date (Medium) | A rollup's stamp is its rebuild date, and the † footnote scopes the stale unit. Any qualifier would be new public wording: folded into ledger item 9 for owner sign-off. |
| DMS note next to red YoY tiles (Medium) | No change. The suggested clause ("does not materially affect …") would assert something the pipeline cannot know in general. |
| Rollup footnotes defer the unit name to the child page; symbol legend; warnings-banner scoping (Low) | No change (W12 pattern). The banner scoping belongs to ledger item 10. |
