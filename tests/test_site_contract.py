import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _leaf_unit_count():
    """Award-ledger leaf units (NSF divisions + NIH institutes/centers) from
    config/orgs.json, independent of anything the site computes -- the
    Phase 3.2d remediation decision-4 coverage line derives the same count
    in the browser from data/index.json's nav leaves."""
    orgs = json.loads((REPO / "config" / "orgs.json").read_text())
    total = 0
    for agency in orgs["agencies"]:
        for directorate in agency.get("directorates", []):
            total += len(directorate.get("divisions", []))
    return total


def _obligation_registry_counts():
    """(accountCount, agencyCount) from config/obligation_accounts.json,
    independent of anything the site computes."""
    config = json.loads(
        (REPO / "config" / "obligation_accounts.json").read_text()
    )
    accounts = config["accounts"]
    agencies = {account["path"].split("/")[0] for account in accounts}
    return len(accounts), len(agencies)


class SiteContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (Path(__file__).resolve().parent.parent / "site" / "index.html").read_text()

    def test_awards_remain_backward_compatible(self):
        self.assertIn('const kind = data.kind || "awards"', self.html)
        self.assertIn('if (kind !== "awards")', self.html)

    def test_obligation_namespace_and_signed_copy(self):
        for text in ("data/obligations/index.json", "renderObligationNotes",
                     "fmtSignedMoney", "Reported in submission periods",
                     "File C is award-financial enrichment",
                     "publicUSAspendingAwardUrl(flow.awardUrl)"):
            self.assertIn(text, self.html)

    def test_obligation_copy_identifies_time_and_ratio_scopes(self):
        for text in ("File C / net", "File B − File C residual",
                     "submissionPeriodDisplay(asOf)",
                     "Distinct File C-linked awards, FY${data.currentFY} to date (not new awards)",
                     "Positive ledger entries, FY${data.currentFY} to date",
                     "Negative ledger entries, FY${data.currentFY} to date",
                     "negative reconciliation residuals",
                     "sign alone does not establish cancellation",
                     "partial source history"):
            self.assertIn(text, self.html)

    def test_obligation_schema_v2_and_render_gate_are_hard_requirements(self):
        self.assertIn("data.schemaVersion !== 2", self.html)
        self.assertIn("fileCToNetRatio", self.html)
        self.assertNotIn("fileCCoverage", self.html)
        self.assertIn('dataset.renderComplete = "true"', self.html)
        self.assertIn("dataset.networkError", self.html)

    def test_charts_are_named_and_secondary_text_meets_contrast_target(self):
        self.assertIn('"aria-labelledby": plot.getAttribute("aria-labelledby")', self.html)
        self.assertIn("--muted: #73716b", self.html)

    def test_partial_cumulative_charts_stop_at_the_dashboard_as_of_date(self):
        self.assertIn("const generatedFiscalDay = data => {", self.html)
        self.assertIn("const displayThroughDay = generatedFiscalDay(data);", self.html)
        self.assertIn(
            "s.partial && s.fy === data.currentFY && displayThroughDay != null",
            self.html,
        )
        self.assertIn("s.points.filter(p => p.d <= displayThroughDay)", self.html)

    def test_site_shell_uses_a_self_contained_favicon(self):
        self.assertIn('<link rel="icon" href="data:image/svg+xml,', self.html)

    def test_long_flow_tables_have_a_current_year_summary(self):
        self.assertIn("rank < 10", self.html)
        self.assertIn("rank < 5", self.html)
        self.assertIn("more flow rows", self.html)
        self.assertIn("Largest award-attributed gross flows", self.html)

    def test_obligation_ledger_is_discoverable_from_award_root(self):
        for text in ("renderViewNav(obligationRoot, sentinelRoot)",
                     "Open the appropriations obligation dashboards",
                     "data/obligations/dashboard.json",
                     "measures are not additive or directly comparable"):
            self.assertIn(text, self.html)

    def test_interpretation_note_renders_as_a_note_not_a_warning(self):
        # Phase 3.2d remediation decision 3: an agency-neutral registry
        # field (`interpretationNote`) is the only switch -- rendered on any
        # account/PA dashboard that carries it, with no agency name check,
        # styled distinctly from the red `.banner` warnings block.
        for text in (
            "function renderInterpretationNote(text, container = $app)",
            "renderInterpretationNote(data.interpretationNote)",
            ".interpretation-note {",
            "border-left: 3px solid var(--muted)",
        ):
            self.assertIn(text, self.html)
        # No agency name may gate whether the note renders.
        self.assertNotIn('"dod"', self.html)
        self.assertNotIn("Department of Defense", self.html)

    def test_landing_table_carries_a_row_note_for_interpretation_note_children(self):
        for text in (
            "const hasNote = Boolean(c.interpretationNote)",
            'unitLabel(c) + (hasNote ? " *" : "")',
            "interpretationNoteFootnotes",
        ):
            self.assertIn(text, self.html)

    def test_stale_account_note_renders_exact_wording_on_account_pages(self):
        # Phase 3.2d remediation W12 (per-account atomicity + published
        # staleness): the header note's wording is fixed and owner-approved
        # verbatim text -- only the date varies.
        for text in (
            "function renderStaleNote(freshness, container = $app)",
            'const staleAccountNoteText = staleSince =>',
            "`Not refreshed since ${staleSince}: the most recent scheduled "
            "pull for this account did not complete; figures are the last "
            "accepted snapshot.`",
            'if (node.level === "account") renderStaleNote(data.freshness);',
            'id: "staleNote"',
        ):
            self.assertIn(text, self.html)

    def test_landing_table_carries_a_dagger_marker_for_stale_rows(self):
        for text in (
            'const isStale = c.refreshStatus?.status === "stale";',
            'text: unitLabel(c) + (hasNote ? " *" : "") + (isStale ? " †" : "")',
            'id: "staleFootnotes"',
            'el("strong", { text: `† ${names.join(", ")}: ` })',
        ):
            self.assertIn(text, self.html)

    def test_stale_unit_note_renders_exact_wording_on_award_pages(self):
        # Phase 3.2d remediation W17 (award-pipeline atomicity, the
        # award-ledger analogue of W12 above): the header note's wording is
        # the same owner-approved verbatim text as the obligation account
        # note, with "account" -> "unit" -- only the date varies. It gates
        # on `refreshStatus.unit` (present on a stale leaf's own dashboard,
        # and on a rollup node that aggregates exactly one leaf, e.g. an
        # NIH passthrough directorate) rather than on node.level, since a
        # multi-leaf rollup's own aggregate refreshStatus carries no `unit`.
        for text in (
            "function renderUnitStaleNote(refreshStatus, container = $app)",
            'const staleUnitNoteText = staleSince =>',
            "`Not refreshed since ${staleSince}: the most recent scheduled "
            "pull for this unit did not complete; figures are the last "
            "accepted snapshot.`",
            'if (!refreshStatus || refreshStatus.status !== "stale" || '
            '!refreshStatus.unit) return;',
            "renderUnitStaleNote(data.refreshStatus);",
            'id: "staleNote"',
        ):
            self.assertIn(text, self.html)
        # Keep the obligation account note text byte-identical -- both
        # sentences (account and unit) must still be present unchanged.
        self.assertIn(
            "`Not refreshed since ${staleSince}: the most recent scheduled "
            "pull for this account did not complete; figures are the last "
            "accepted snapshot.`",
            self.html,
        )

    def test_stale_unit_page_stamp_names_the_snapshot_date(self):
        # W17 reader review (2026-09-23): on a single stale unit's page the
        # "last updated" stamp must name the last accepted snapshot's date
        # (refreshStatus.staleSince), not the rollup rebuild date, or the
        # stamp contradicts the "Not refreshed since" note beside it.
        for text in (
            'const unitStale = data.refreshStatus?.status === "stale" && '
            'data.refreshStatus.unit && data.refreshStatus.staleSince;',
            "const lastUpdated = unitStale ? "
            'new Date(data.refreshStatus.staleSince + "T12:00:00") : gen;',
            "last updated ${lastUpdated.toLocaleDateString(",
        ):
            self.assertIn(text, self.html)

    def test_award_landing_table_carries_a_dagger_marker_for_stale_rows(self):
        # Phase 3.2d remediation W17: the award childrenCard's dagger +
        # footnote pattern, exactly parallel to obligationChildrenCard's
        # (W12) -- a separate id-free row suffix (award rows have no
        # interpretationNote asterisk to share with) grouped by identical
        # `reason` text.
        for text in (
            'const isStale = c.refreshStatus?.status === "stale";',
            'text: unitLabel(c) + (isStale ? " †" : "")',
            'id: "staleFootnotes"',
            'el("strong", { text: `† ${names.join(", ")}: ` })',
            "const text = c.refreshStatus.reason;",
        ):
            self.assertIn(text, self.html)

    def test_award_root_coverage_line_and_obligation_subtitles_are_derived(self):
        # Phase 3.2d remediation decision 4 (fixed wording; counts derived
        # in the browser, never hardcoded).
        self.assertIn(
            "`Award ledger: NIH and NSF, ${fmtN(unitCount)} units. "
            "Obligation ledger: ${fmtN(accountCount)} registered federal "
            "accounts across ${fmtN(agencyCount)} agencies.`",
            self.html,
        )
        self.assertIn(
            "`Obligations from ${fmtN(data.accountCount ?? 0)} registered "
            "science-related federal accounts, including defense RDT&E. "
            "They are separate from, and not additive to, the award "
            "totals on the award dashboards. Negative entries can "
            "include routine corrections or reductions; sign alone does "
            "not establish a cancellation.`",
            self.html,
        )
        self.assertIn("function countLeaves(node) {", self.html)
        # No number in the fixed wording is a hardcoded literal.
        self.assertNotIn("NIH and NSF, 87 units", self.html)
        self.assertNotIn("from 53 registered", self.html)

    def test_award_root_coverage_numbers_match_the_registries(self):
        # Pins the meaning of the fixed wording independent of rendering:
        # if these ever drift from 87/53/13, the wording itself (owner-
        # approved verbatim text) would need a fresh owner decision, not a
        # silent code change.
        self.assertEqual(87, _leaf_unit_count())
        account_count, agency_count = _obligation_registry_counts()
        self.assertEqual(53, account_count)
        self.assertEqual(13, agency_count)

    def test_award_ledger_renders_w1_methodology_and_data_quality_fields(self):
        for text in (
            "function renderMethodologyNote(text) {",
            "function renderDataQualityNotes(notes) {",
            "renderMethodologyNote(data.methodologyNote)",
            "renderDataQualityNotes([...(data.dataQualityNotes || []), ...dedupNotices(data.warnings)])",
            'id: "methodologyNote"',
            'id: "dataQualityNotes"',
        ):
            self.assertIn(text, self.html)
        # dataQualityNotes must not render through the red warnings banner.
        methodology_block = self.html.split(
            "function renderDataQualityNotes(notes) {", 1
        )[1].split("function renderMethodologyNote", 1)[0]
        self.assertNotIn('class: "banner"', methodology_block)

    def test_award_root_carries_no_obligation_figures_only_a_link_card(self):
        # Display-improvements batch item 3 (2026-09-23, owner-approved):
        # each tab shows one kind of figure -- the award root no longer
        # renders any obligation dollar figures, only a cross-link card.
        for text in (
            'heading: "Award activity"',
            'const linkCard = el("div", { class: "card", id: "obligationLinkCard" });',
            'text: "Appropriations obligations"',
            "Account-level signed obligations are separate from award "
            "totals because the measures are not additive or directly "
            "comparable.",
            "Open the appropriations obligation dashboards",
            'href: "index.html?org=obligations"',
        ):
            self.assertIn(text, self.html)
        self.assertNotIn("obligationTiles(obligationSummary", self.html)
        self.assertNotIn("obligationChildrenCard(obligationSummary", self.html)

    def test_obligation_reporting_periods_use_a_signed_line_chart(self):
        chart = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        chart = chart.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn("the line is not cumulative", chart)
        self.assertIn('const line = rows.map', chart)
        self.assertIn('f.svg.append(el("path"', chart)
        self.assertIn('f.svg.addEventListener("pointermove"', chart)
        self.assertNotIn("const bar =", chart)

    def test_sentinel_is_discoverable_and_has_a_hard_schema_gate(self):
        for text in ('label: "Funding-action sentinel"',
                     'href: "index.html?org=sentinel"',
                     'if (kind === "sentinel")',
                     "data.schemaVersion !== 1",
                     "renderSentinel(data)"):
            self.assertIn(text, self.html)

    def test_sentinel_copy_keeps_evidence_and_states_separate(self):
        for text in ("A signal is not a cancellation",
                     "Unreviewed signal", "Source-confirmed event",
                     "Reviewed finding", "Superseded", "Restored",
                     "gross negative activity",
                     "net activity", "Attributed source headline",
                     "Optional review finding"):
            self.assertIn(text, self.html)

    def test_sentinel_card_language_matches_remediation_decision_5(self):
        # Phase 3.2d remediation decision 5 (owner-approved, sentinel-facing
        # language): "affected award IDs" -> "award IDs with negative
        # entries"; "(not overdue)" dropped, age shown alone; a state line
        # when net activity in a period was positive; gross negative and
        # net shown side by side in the card header.
        for text in (
            "award IDs with negative entries",
            "net activity in this period was positive",
            "sentinel-header-figures",
        ):
            self.assertIn(text, self.html)
        for retired in ("affected award IDs", "(not overdue)"):
            self.assertNotIn(retired, self.html)

    def test_sentinel_surfaces_source_confirmed_episodes_and_bounds_page_height(self):
        # Independent-review finding: 2 source-confirmed episodes were
        # unfindable among 170 unreviewed ones, and a full unreviewed
        # listing produced a page tall enough that a full-page screenshot
        # clipped the final card and left a large blank tail. Fixed by an
        # always-visible #confirmed section plus a bounded inline count with
        # the rest behind a native <details> (unopened <details> content is
        # not laid out, so it does not add to the rendered page height).
        for text in (
            'id: "confirmed"',
            "SENTINEL_INLINE_EPISODE_LIMIT",
            'el("details", { class: "detail-table" })',
            "sentinelEpisodeCard(episode, data, details)",
        ):
            self.assertIn(text, self.html)

    def test_attributed_source_fields_render_only_through_the_shared_helper(self):
        # Owner-approved 2026-08-12 rule: render by provenance, not judgment.
        # Every authoritative-source display string (announcement titles,
        # stated reasons, qualified amount display strings) must route
        # through the single attributedText() helper — never be interpolated
        # directly into a heading, link, or plain text node.
        self.assertIn("function attributedText(text, source,", self.html)
        # Required: each attributed field is passed into the helper.
        for text in (
            "attributedText(event.sourceTitle || label, source, { omitCitation: true })",
            "attributedText(announcedDisplay, source, { omitCitation: true })",
            "attributedText(first.sourceTitle || first.sourceId, source, { omitCitation: true })",
            "attributedText(null, source)",
        ):
            self.assertIn(text, self.html)
        # statedReason is an adapter paraphrase, never a verbatim quote:
        # it must render unquoted AND carry the paraphrase label, so neither
        # the helper (which quotes) nor a bare interpolation is acceptable.
        self.assertIn(
            '"Stated reason (paraphrase, not verbatim): " + event.statedReason',
            self.html)
        self.assertNotIn("attributedText(event.statedReason", self.html)
        # Forbidden: verbatim fields must never be interpolated directly into
        # a heading, link, or plain text node outside the helper call.
        for text in (
            'el("a", { href: event.sourceUrl, text: event.sourceTitle',
            'el("a", { href: first.sourceUrl, text: first.sourceTitle',
            "text: event.sourceTitle",
            "text: event.statedReason",
            "text: announcedDisplay",
            "text: first.sourceTitle",
        ):
            self.assertNotIn(text, self.html)

    def test_sourced_episode_headings_are_mechanical_never_a_source_headline(self):
        # Owner-approved 2026-08-12 rule: agency headlines never occupy
        # heading positions, even quoted. Sourced-episode headings are
        # composed mechanically from structured fields; only financial-
        # observation episodes (no sourcedEvents) fall back to their
        # registry program-activity title.
        self.assertIn("function sourcedEpisodeHeading(episode) {", self.html)
        self.assertIn("function episodeHeadingText(episode, data) {", self.html)
        self.assertIn('el("h2", { text: episodeHeadingText(episode, data) })', self.html)
        # The old pattern that rendered a raw episode.title as the card
        # heading must not reappear.
        self.assertNotIn('el("h2", { text: episode.title', self.html)

    def test_sentinel_card_drops_the_unreviewed_age_counter(self):
        # Display-improvements batch item 6 (2026-09-23, W17 reader review
        # #8, owner sign-off norm): "unreviewed for N days" reads as an SLA
        # the page's own text disclaims -- dropped entirely, never rendered.
        self.assertNotIn("unreviewed for", self.html)
        self.assertNotIn("unreviewedAgeDays", self.html)
        self.assertIn(
            'card.append(el("p", { class: "note", '
            'text: `Observed ${observed || "date unavailable"}` }));',
            self.html,
        )

    def test_financial_episode_headings_compose_account_and_fiscal_year(self):
        # Display-improvements batch item 6 (2026-09-23, W17 reader review
        # #4, owner sign-off norm): repeated identical program-activity
        # titles across episodes invite double-counting -- a
        # financial-observation episode's heading (no sourcedEvents) now
        # adds the account abbreviation and fiscal year it covers, both
        # derived from structured fields only.
        self.assertIn("function financialEpisodeHeading(episode, data) {", self.html)
        heading_fn = self.html.split("function financialEpisodeHeading(episode, data) {", 1)[1]
        heading_fn = heading_fn.split("function episodeHeadingText(episode, data) {", 1)[0]
        self.assertIn("data?.coverage?.financialAccounts", heading_fn)
        self.assertIn(".join(\", \")", heading_fn)
        self.assertIn("`FY${fys[0]}–FY${fys.at(-1)}`", heading_fn)
        self.assertIn('.filter(Boolean).join(" · ")', heading_fn)
        self.assertIn(
            "return (episode.sourcedEvents || []).length\n"
            "    ? sourcedEpisodeHeading(episode)\n"
            "    : financialEpisodeHeading(episode, data);",
            self.html,
        )

    def test_not_reported_period_renders_a_hollow_marker_and_table_text(self):
        # Owner decision 2 (2026-09-17, Phase 3.2d remediation): the period
        # activity chart omits a notReported period; the cumulative step
        # holds the last reported value and draws a hollow marker there;
        # the table row reads exactly "not reported at pull".
        self.assertIn('const NOT_REPORTED_AT_PULL = "not reported at pull";', self.html)
        cumulative = self.html.split("function obligationCumulativeChart(data) {", 1)[1]
        cumulative = cumulative.split("function obligationPeriodsChart(data) {", 1)[0]
        self.assertIn("p.held", cumulative)
        self.assertIn('fill: css("--surface"), stroke: css(s.v)', cumulative)
        self.assertIn("marker.append(svgTitle(NOT_REPORTED_AT_PULL))", cumulative)
        self.assertIn('"aria-label": NOT_REPORTED_AT_PULL', cumulative)
        self.assertIn("NOT_REPORTED_AT_PULL", cumulative)
        periods = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        periods = periods.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn('r.status === "notReported"', periods)
        self.assertIn("NOT_REPORTED_AT_PULL", periods)
        self.assertIn("covers", periods)
        self.assertIn("coversPeriods", periods)
        # The period activity chart itself omits notReported rows.
        self.assertIn(
            'const rows = allRows.filter(r => (r.status || "reported") !== "notReported");',
            periods)

    def test_cumulative_chart_skips_null_valued_held_points(self):
        # Phase 3.2d remediation W14 (2026-09-21): a notReported point with
        # no earlier reported point in the fiscal year carries a null
        # cumulative (adapters.obligation_common.aggregate), not $0 --
        # commerce/noaa-orf FY2024 P02-P11 previously drew a false flat-zero
        # line before the first real reported point (P12). The chart must
        # filter such points out of the drawn line, the endpoint/hollow
        # markers, the hover lookup, and the y-axis domain.
        cumulative = self.html.split("function obligationCumulativeChart(data) {", 1)[1]
        cumulative = cumulative.split("function obligationPeriodsChart(data) {", 1)[0]
        self.assertIn(
            "s.points.filter(p => p.netObligationsCents != null)", cumulative)
        self.assertIn(
            "p.d <= day && p.netObligationsCents != null", cumulative)
        self.assertIn(
            ".filter(p => p.netObligationsCents != null)", cumulative)
        # The line/marker loop draws from the filtered ``visible`` list, not
        # the raw (possibly null-leading) ``s.points``.
        self.assertIn("const visible = s.points.filter", cumulative)
        self.assertIn("visible.map((p, i)", cumulative)
        self.assertIn("visible.at(-1)", cumulative)
        # The period table still reads "not reported at pull" for a held
        # point regardless of whether it carries a real held-over value or
        # a null one -- unchanged, keyed only on `p.held`.
        self.assertIn("rows.push(p.held", cumulative)

    def test_period_notes_render_below_the_fy_chart_as_source_figure_statements(self):
        # Phase 3.2d remediation W16: curated `periodNotes.publicNote`
        # values render as a small reader-facing block, without cause
        # attribution, directly below the fiscal-year period table /
        # cumulative chart -- same presence-driven pattern as
        # interpretationNote, no agency check.
        for text in (
            "function renderPeriodNotes(notes, container = $app)",
            "Notes on source figures",
            'id: "periodNotes"',
            "renderPeriodNotes(data.periodNotes)",
        ):
            self.assertIn(text, self.html)
        call_site = self.html.split("if (data.fiscalYears?.length) renders.push(obligationFYChart(data));", 1)[1]
        call_site = call_site.split("obligationFlowTables(data);", 1)[0]
        self.assertIn("renderPeriodNotes(data.periodNotes)", call_site)
        self.assertIn(
            'text: `FY${n.fy}, period ${n.period}: ${n.note}`', self.html
        )

    def test_period_notes_appear_in_the_two_curated_account_dashboards(self):
        # The two accounts with a curated publicNote (docs/obligation-ledger.md
        # "periodNotes") must carry the exact reader-facing text in their
        # rolled-up account dashboard.json after scripts/rollup_obligations.py.
        cases = [
            (
                REPO / "data" / "obligations" / "commerce" / "nist-its" / "dashboard.json",
                "In fiscal year 2025, period 11, the source reports a net "
                "deobligation of $5.03 billion, taking cumulative net "
                "obligations for the year from $5.73 billion after period "
                "10 to $0.70 billion. The fiscal-year-end total (GTAS/File "
                "A) reconciles to the post-deobligation figure.",
            ),
            (
                REPO / "data" / "obligations" / "dhs" / "cisa-rd" / "dashboard.json",
                "In fiscal year 2023, the source's period 3 snapshot "
                "reported cumulative net obligations of $12.90 million, "
                "above the fiscal-year-end total of $9.85 million. From "
                "period 4 (cumulative $1.00 million) onward, the source's "
                "figures are consistent with the year-end total.",
            ),
        ]
        for path, public_note in cases:
            dashboard = json.loads(path.read_text())
            notes = dashboard.get("periodNotes")
            self.assertTrue(notes, f"{path} missing periodNotes")
            self.assertIn(public_note, [n["note"] for n in notes])
            # Internal curator text (run ids, cents) must never appear here.
            for n in notes:
                self.assertNotIn("run 3", n["note"])

    def test_cisa_decline_caption_is_a_curated_source_figure_note(self):
        # Stage 2 item 8 (owner-approved 2026-09-23): the DHS CISA R&D
        # decline gets a source-figure statement with no cause attribution,
        # carried by the existing periodNotes mechanism (baseline publicNote
        # -> scripts/rollup_obligations.py -> account dashboard.json), never
        # by an agency-conditional code path in the site.
        caption = ("The source reports $3.31 million for this account in "
                   "FY2024 and $98 in FY2025. Source figures alone do not "
                   "show whether the activity ended or moved to another "
                   "account.")
        baseline = json.loads(
            (REPO / "reference" / "dhs_cisa_rd_obligation_baseline.json").read_text())
        notes = baseline["fiscalYears"]["2025"]["periodNotes"]
        self.assertIn(caption, [n.get("publicNote") for n in notes])
        dashboard = json.loads(
            (REPO / "data" / "obligations" / "dhs" / "cisa-rd" / "dashboard.json").read_text())
        self.assertIn({"fy": 2025, "period": 12, "note": caption}, dashboard["periodNotes"])
        self.assertNotIn("cisa", self.html.lower())

    def test_sentinel_publishes_limits_costs_and_source_staleness(self):
        for text in ("Coverage and interpretation limits",
                     "Current automated financial coverage",
                     "Current authoritative-source coverage",
                     "Absence from this page is not evidence that no funding action occurred",
                     "Estimated pilot burden",
                     "Replace them with measured figures after eight weeks",
                     "retains its last accepted records",
                     "Other dashboards and deployments continue independently"):
            self.assertIn(text, self.html)

    def test_monthly_chart_marks_the_in_progress_month_distinct(self):
        # Reader review (High): the still-accruing current month must never
        # be drawn identically to a complete month -- it reads as a
        # collapse in awards rather than a partial count. Item 11.
        self.assertIn("const awardAsOfDate = data =>", self.html)
        chart = self.html.split("function monthlyChart(data) {", 1)[1]
        chart = chart.split("function fyAwardsChart(data, windowDone) {", 1)[0]
        self.assertIn(
            "Every month since October 2014. Months with zero awards are "
            "shown as zero. The last point is the current month to date "
            "— a partial count, drawn dashed with an open marker.",
            chart,
        )
        self.assertIn('"stroke-dasharray"', chart)
        self.assertIn(" to date`", chart)
        self.assertIn('fill: css("--surface")', chart)
        self.assertIn("(to date)", chart)

    def test_obligation_cadence_caption_appears_on_both_step_charts(self):
        # Display-improvements batch item 1: the reporting-cadence caveat is
        # a shared constant rendered on both obligation step charts, never a
        # copy-pasted string.
        self.assertIn(
            'const OBLIGATION_CADENCE_CAPTION = "obligations are reported '
            'in monthly agency submission periods; steps reflect reporting '
            'cadence, not action dates.";',
            self.html,
        )
        cumulative = self.html.split("function obligationCumulativeChart(data) {", 1)[1]
        cumulative = cumulative.split("function obligationPeriodsChart(data) {", 1)[0]
        self.assertIn("OBLIGATION_CADENCE_CAPTION", cumulative)
        periods = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        periods = periods.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn("OBLIGATION_CADENCE_CAPTION", periods)

    def test_obligation_periods_chart_is_a_step_chart(self):
        # Display-improvements batch item 1: explicit step geometry (owner
        # request) -- flat steps in equal-width slots joined by vertical
        # risers, never a sloped point-to-point line.
        periods = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        periods = periods.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn('makeCard("Net obligations by reporting period",', periods)
        self.assertIn(
            "Each step is signed activity in one agency submission period; "
            "the line is not cumulative. The first P02 step covers the "
            "first reporting window; quarterly reporters appear only at "
            "quarter end. A period not reported at pull is omitted from "
            "the chart and shown in the table below.",
            periods,
        )
        self.assertIn("V${", periods)
        self.assertIn("H${", periods)
        self.assertIn(", periodLabel(r), tipRows)", periods)

    def test_obligation_periods_chart_notes_curated_periods_without_correction_language(self):
        # Display-improvements batch item 5: inline callouts for curated
        # source-figure notes (dhs/cisa-rd FY2023P04, commerce/nist-its
        # FY2025P11 today), never described as a "correction".
        periods = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        periods = periods.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn("notedPeriods", periods)
        self.assertIn('"see note"', periods)
        self.assertIn('" (see note)"', periods)
        self.assertIn('"stroke-dasharray": "3 3"', periods)
        self.assertNotIn("correction", periods.lower())

    def test_award_side_labels_use_count_noun_and_dollar_labels(self):
        # Metric-identity audit item 2: award-count chart titles reuse the
        # tiles' provider-aware count noun, and dollar-valued columns/legend
        # entries say so.
        self.assertIn(
            'const awardCountNoun = data => data.provider === "nih" ? '
            '"Award records" : data.provider === "nsf" ? "New awards" : '
            '"Awards";',
            self.html,
        )
        top_awards = self.html.split("function topAwards(data) {", 1)[1]
        top_awards = top_awards.split("function signedDomain(values) {", 1)[0]
        self.assertIn('"FY", "Award", "Institution", "Award $"', top_awards)
        dollars = self.html.split("function dollarsChart(data) {", 1)[1]
        dollars = dollars.split("function cumulativeChart(data, key, title, note, fmtVal, fmtEnd) {", 1)[0]
        self.assertIn('{ label: "All other awards ($)"', dollars)
        self.assertIn('{ label: "Top 3 awards ($)"', dollars)
        self.assertIn("`${awardCountNoun(data)} per month`", self.html)
        self.assertIn("`${awardCountNoun(data)} by fiscal year (Oct–Jul)`", self.html)
        self.assertIn("`${awardCountNoun(data)} by mechanism (Oct–Jul)`", self.html)
        self.assertIn(
            '`Cumulative ${awardCountNoun(data).toLowerCase()} through the fiscal year`',
            self.html,
        )

    def test_empty_file_c_sections_get_an_inline_placeholder(self):
        # Display-improvements batch item 4 (reader review #5): a shown
        # fiscal year with zero File C rows linked to public awards gets an
        # inline placeholder instead of a header-only empty table or a
        # silently absent card.
        self.assertIn(
            'const emptyFileCRowsNote = label =>\n'
            '  el("p", { class: "note empty-section", '
            'text: `No File C rows linked to public awards in ${label}.` });',
            self.html,
        )
        flow_tables = self.html.split("function obligationFlowTables(data) {", 1)[1]
        # Both cards now gate on `years.length`, not on having any rows, so
        # a shown year with no rows still renders the card with a
        # placeholder rather than disappearing or leaving a header-only
        # empty table.
        self.assertIn("if (years.length) {", flow_tables)
        self.assertIn("if (!years.length) return;", flow_tables)
        self.assertIn("emptyFileCRowsNote(yearRange)", flow_tables)
        self.assertIn("emptyFileCRowsNote(`FY${years[0].fy}`)", flow_tables)
        self.assertIn(
            "card.append(primary.length ? recipientTable(primary) : "
            "emptyFileCRowsNote(`FY${years[0].fy}`));",
            flow_tables,
        )
        self.assertIn(
            "card.append(primary.length ? flowTable(primary) : "
            "emptyFileCRowsNote(`FY${years[0].fy}`));",
            flow_tables,
        )

    def test_obligation_stamp_labels_the_all_years_total_horizon(self):
        # Display-improvements batch item 7 (reader review #10): the
        # all-years total sits directly above a current-FY tile with no
        # horizon of its own -- label the fiscal-year span it sums over.
        boot = self.html.split('if (kind === "obligations") {', 1)[1]
        boot = boot.split('if (kind !== "awards")', 1)[0]
        self.assertIn(
            "const fyRange = (() => {\n"
            "      const fys = (data.fiscalYears || []).map(f => f.fy);\n"
            "      if (!fys.length) return \"\";\n"
            "      const a = Math.min(...fys), b = Math.max(...fys);\n"
            "      return a === b ? `FY${a}` : `FY${a}–FY${b} combined`;\n"
            "    })();",
            boot,
        )
        self.assertIn(
            "`${fmtSignedMoney(totalNet)} net obligations across "
            "${fmtN(data.distinctLinkedAwards || 0)} distinct linked awards"
            "${fyRange ? `, ${fyRange}` : \"\"} · through "
            "${submissionPeriodDisplay(asOf)} · last updated "
            "${gen.toLocaleDateString(\"en-US\", { month: \"long\", "
            "day: \"numeric\", year: \"numeric\" })}`",
            boot,
        )
        # The pending-pull path overwrites the stamp afterward and must stay
        # untouched by this change.
        self.assertIn(
            '"Initial obligation-ledger pull pending"',
            boot,
        )

    def test_stale_footnote_is_a_shared_helper(self):
        # Display-improvements batch item 9 (W17 reader review): the grouped
        # "† <names>: <reason>" footnote paragraph is built once and reused
        # by both landing tables and both tile groups, so the literal text
        # (pinned by the older per-table tests above) can never drift
        # between call sites.
        self.assertIn("function staleFootnote(staleRows, { id } = {}) {", self.html)
        for text in (
            "const text = c.refreshStatus.reason;",
            'el("strong", { text: `† ${names.join(", ")}: ` })',
            'const p = el("p", { class: "note", id });',
        ):
            self.assertIn(text, self.html)
        # Both tables call the shared helper rather than rebuilding it.
        self.assertIn(
            'card.append(staleFootnote(staleRows, { id: "staleFootnotes" }));',
            self.html,
        )

    def test_landing_table_numeric_cells_carry_the_dagger_on_stale_rows(self):
        # Item 9: a stale row's numeric cells, not just its name cell, must
        # carry the " †" disclosure -- a reader scanning figures rather than
        # names must not miss it. A "no data yet" row is unaffected.
        children_card = self.html.split("function childrenCard(data) {", 1)[1]
        children_card = children_card.split("function obligationChildrenCard(", 1)[0]
        self.assertIn('const daggerSuffix = isStale ? " †" : "";', children_card)
        self.assertIn("fmtN(c.octJulAwards) + daggerSuffix", children_card)
        self.assertIn("pctTxt + daggerSuffix", children_card)
        self.assertIn("fmtMoney(c.octJulDollars) + daggerSuffix", children_card)
        self.assertIn("fmtN(c.totalAwards) + daggerSuffix", children_card)
        # The "no data yet" branch is untouched.
        self.assertIn('el("td", { class: "num", text: "no data yet" })', children_card)

        obligation_card = self.html.split("function obligationChildrenCard(data, title = null, note = null) {", 1)[1]
        obligation_card = obligation_card.split("function childrenCardFromIndex(", 1)[0]
        self.assertIn('const daggerSuffix = isStale ? " †" : "";', obligation_card)
        self.assertIn("fmtSignedMoney(value) + daggerSuffix", obligation_card)
        self.assertIn("fmtCoverage(c.fileCToNetRatio) + daggerSuffix", obligation_card)
        self.assertIn("fmtN(c.distinctLinkedAwards || 0) + daggerSuffix", obligation_card)
        self.assertIn('el("td", { class: "num", text: "no data yet" })', obligation_card)

    def test_tile_groups_mark_values_and_render_a_footnote_for_stale_children(self):
        # Item 9: the page's topline tiles carry the same disclosure when at
        # least one of the page's own children is stale, with the same
        # grouped footnote directly below the tile row -- distinct ids so
        # they never collide with the table's "staleFootnotes" or with each
        # other.
        self.assertIn("function appendTileGroup(row, { id = \"\", heading = \"\", note = \"\", footnote = null } = {}) {", self.html)
        self.assertIn("if (footnote) $app.append(footnote);", self.html)
        self.assertIn("if (footnote) section.append(footnote);", self.html)

        tiles_fn = self.html.split("function tiles(data, options = {}) {", 1)[1]
        tiles_fn = tiles_fn.split("// The as-of date of an award dashboard", 1)[0]
        self.assertIn(
            "const staleChildren = data.refreshStatus?.unit\n"
            "    ? []\n"
            '    : (data.children || []).filter(c => c.refreshStatus?.status === "stale");',
            tiles_fn,
        )
        self.assertIn('text: s.val + tileDagger', tiles_fn)
        self.assertIn(
            'staleFootnote(staleChildren, { id: "tileStaleFootnotes" })', tiles_fn)

        obligation_tiles_fn = self.html.split("function obligationTiles(data, options = {}) {", 1)[1]
        obligation_tiles_fn = obligation_tiles_fn.split("const NOT_REPORTED_AT_PULL", 1)[0]
        self.assertIn(
            'const staleChildren = (data.children || []).filter(c => c.refreshStatus?.status === "stale");',
            obligation_tiles_fn,
        )
        self.assertIn('text: value + tileDagger', obligation_tiles_fn)
        self.assertIn(
            'staleFootnote(staleChildren, { id: "obligationTileStaleFootnotes" })',
            obligation_tiles_fn,
        )

    def test_award_tiles_skip_the_dagger_on_a_single_stale_units_own_page(self):
        # Item 9 exception: a single stale unit's own page (or a one-leaf
        # passthrough rollup) already carries the "Not refreshed since"
        # header note directly above the tiles (renderUnitStaleNote) --
        # marking the tiles too would be redundant, not additive.
        tiles_fn = self.html.split("function tiles(data, options = {}) {", 1)[1]
        tiles_fn = tiles_fn.split("// The as-of date of an award dashboard", 1)[0]
        self.assertIn("data.refreshStatus?.unit", tiles_fn)

    def test_warnings_banner_glosses_raw_validator_text(self):
        # Display-improvements batch item 10 (2026-09-23, W17 reader review
        # round 2, owner sign-off on public-claim wording): a raw validator
        # string reads to a policy audience as awards being cancelled, not
        # as the pipeline diagnostic it is. One shared helper classifies
        # every warning and renders plain-language glosses, with the raw
        # text kept verbatim behind a <details> for anyone who wants it.
        self.assertIn(
            "function renderWarnings(warnings) {",
            self.html,
        )
        # The dedup routing regex: a "N awards appear in more than one
        # division" notice is not a warning at all.
        self.assertIn(
            '["dedup", /appears? in more than one division; counted once '
            "in this rollup/],",
            self.html,
        )
        # The four gloss strings, verbatim.
        for text in (
            "The stored award count went down since the previous pull. "
            "Stored awards are never deleted, so this flags a pipeline "
            "problem, not cancelled awards.",
            "Some awards already on record were not returned by the "
            "latest pull; they are kept, not removed.",
            "A month's count came in below an independently verified "
            "tally; that month may be incomplete.",
            "An automated consistency check flagged this pull; technical "
            "detail below.",
            "Technical detail",
        ):
            self.assertIn(text, self.html)
        # Both banner sites go through the one helper; the old inline
        # banner-building code is gone from both call sites.
        self.assertIn("renderWarnings(data.warnings);", self.html)
        # Dedup notices join the neutral notes list in ONE call (never a
        # second notes block), and the banner never sees them.
        self.assertIn(
            "renderDataQualityNotes([...(data.dataQualityNotes || []), "
            "...dedupNotices(data.warnings)]);",
            self.html,
        )
        self.assertEqual(1, self.html.count("renderDataQualityNotes(["))

    def test_award_rollup_stamp_gets_a_stale_unit_qualifier(self):
        # Display-improvements batch item 9/12 (2026-09-23, W17 reader
        # review round 2): a multi-leaf rollup (no single stale unit's own
        # page) whose own refreshStatus is stale gets a stamp qualifier
        # naming how many units and since when, so a reader who never
        # scrolls to the landing table or tiles still sees the disclosure.
        self.assertIn("function formatStaleDateRange(dates) {", self.html)
        self.assertIn(
            'if (data.refreshStatus?.status === "stale" && '
            "!data.refreshStatus.unit) {",
            self.html,
        )
        self.assertIn(
            "document.getElementById(\"stamp\").textContent +=\n"
            '      ` · includes ${k} ${k === 1 ? "unit" : "units"} last '
            "refreshed ${dates} †`;",
            self.html,
        )
        # The pinned single-stale-unit lines are untouched.
        self.assertIn(
            'const unitStale = data.refreshStatus?.status === "stale" && '
            'data.refreshStatus.unit && data.refreshStatus.staleSince;',
            self.html,
        )
        self.assertIn(
            "const lastUpdated = unitStale ? "
            'new Date(data.refreshStatus.staleSince + "T12:00:00") : gen;',
            self.html,
        )
        self.assertIn("last updated ${lastUpdated.toLocaleDateString(", self.html)

    def test_obligation_rollup_stamp_gets_a_stale_account_qualifier(self):
        # Display-improvements batch item 9/12: the obligation-side
        # analogue, root or agency level only (an account's own page
        # already carries the "Not refreshed since" header note).
        self.assertIn(
            'if ((node.level === "root" || node.level === "agency")\n'
            "        && (data.children || []).some(c => "
            'c.refreshStatus?.status === "stale")) {',
            self.html,
        )
        self.assertIn(
            "const k = typeof data.staleAccountCount === \"number\" && "
            "data.staleAccountCount > 0\n"
            "        ? data.staleAccountCount : staleChildren.length;",
            self.html,
        )
        self.assertIn(
            "document.getElementById(\"stamp\").textContent +=\n"
            '        ` · includes ${k} ${k === 1 ? "account" : "accounts"} '
            "last refreshed ${dates} †`;",
            self.html,
        )

    def test_obligation_periods_chart_labels_covering_steps_with_a_span(self):
        # Display-improvements batch (reader review): a covering row
        # (coversPeriods.length > 1) absorbs several not-reported periods
        # into one step, but drawn plainly it reads as an ordinary
        # single-period move -- a small "covers Pxx–Pxx" span label at the
        # step, drawn after (so on top of) the step path, discloses the
        # absorbed span directly in the chart, not only in the table.
        periods = self.html.split("function obligationPeriodsChart(data) {", 1)[1]
        periods = periods.split("function obligationFYChart(data) {", 1)[0]
        self.assertIn(
            'if (r.status === "notReported" || !r.coversPeriods || '
            "r.coversPeriods.length <= 1) return;",
            periods,
        )
        self.assertIn(
            "const rawY = value >= 0 ? y(value) - 6 : y(value) + 14;",
            periods,
        )
        self.assertIn(
            "let spanY = Math.max(f.T + 10, Math.min(f.B - 4, rawY));",
            periods,
        )
        self.assertIn(
            "const text = `covers ${short(r.coversPeriods[0])}"
            "–${short(r.coversPeriods.at(-1))}`;",
            periods,
        )
        # Adjacent span labels never overprint: a clashing label moves off.
        self.assertIn("const placedSpans = [];", periods)
        self.assertIn("clashes(spanY)", periods)
        # Drawn after the step path is appended, not before, so the span
        # labels sit on top of the line rather than under it.
        path_pos = periods.index('f.svg.append(el("path", { d: line,')
        span_pos = periods.index("const text = `covers ${short(r.coversPeriods[0])}")
        self.assertLess(path_pos, span_pos)
        # The table's own periodLabel wording (hyphen, not en dash) is
        # untouched by this change.
        self.assertIn(
            "`${r.submissionPeriod} (covers ${short(r.coversPeriods[0])}-"
            "${short(r.coversPeriods.at(-1))})`",
            periods,
        )

    def test_monthly_chart_end_label_clears_the_line_when_in_progress(self):
        # Display-improvements batch (reader review): the in-progress end
        # label used to sit at y(last) - 10 and run left across the line it
        # was labeling. Placed above the higher of the last complete point
        # and the last point instead, clamped to stay on the plot.
        chart = self.html.split("function monthlyChart(data) {", 1)[1]
        chart = chart.split("function fyAwardsChart(data, windowDone) {", 1)[0]
        self.assertIn(
            "const lastLabelY = (anyInProgress && lastComplete >= 0)\n"
            "        ? Math.max(f.T + 12, Math.min(y(pts[lastComplete].awards), "
            "y(pts[last].awards)) - 10)\n"
            "        : y(pts[last].awards) - 10;",
            chart,
        )
        self.assertIn(
            'f.svg.append(el("text", { class: "dlabel", x: x(last) - 6, '
            'y: lastLabelY, "text-anchor": "end", text: lastLabel }));',
            chart,
        )

    def test_numeric_table_cells_never_wrap(self):
        # Display-improvements batch (reader review): a minus sign wrapping
        # onto its own line in a numeric table cell reads as stray
        # punctuation next to the wrapped figure below it.
        self.assertIn("td.num, th.num { white-space: nowrap; }", self.html)

    def test_mechanism_chart_end_labels_use_fmtN_and_clear_the_frame(self):
        # Display-improvements batch (reader review): "28776 continuin" --
        # the unformatted number plus a right padding of 118 clipped the end
        # label ("28,776 continuing") off the plot at common widths.
        mechanism = self.html.split("function mechanismChart(data) {", 1)[1]
        mechanism = mechanism.split("function dollarsChart(data) {", 1)[0]
        self.assertIn("const f = frame(plot, 300, 46, 150);", mechanism)
        self.assertIn(
            'text: `${fmtN(last)} ${s.label.split(" ")[0].toLowerCase()}` }));',
            mechanism,
        )

    def test_zero_net_obligation_program_activities_collapse_on_account_pages(self):
        # Display-improvements batch (reader review): an account's
        # program-activity table listed dozens of $0-current-FY rows
        # interleaved with active ones, reading as those named programs
        # having been eliminated. Split into a collapsed <details> directly
        # after the main table, account level only, reusing the same row
        # builder so columns and stale/interpretation-note markers never
        # drift between the two tables.
        children_card = self.html.split(
            "function obligationChildrenCard(data, title = null, note = null) {", 1
        )[1]
        children_card = children_card.split("function childrenCardFromIndex(", 1)[0]
        self.assertIn("const buildRow = c => {", children_card)
        self.assertIn("const buildTable = rows => {", children_card)
        self.assertIn(
            'const zeroRows = data.node?.level === "account"\n'
            "    ? sorted.filter(c => c.hasData && "
            "(c.currentFYNetObligations || 0) === 0)\n"
            "    : [];",
            children_card,
        )
        self.assertIn(
            "const splitZeroRows = zeroRows.length > 0 && "
            "zeroRows.length < sorted.length;",
            children_card,
        )
        self.assertIn(
            "const mainRows = splitZeroRows ? "
            "sorted.filter(c => !zeroRows.includes(c)) : sorted;",
            children_card,
        )
        self.assertIn(
            '`Show ${n} program ${n === 1 ? "activity" : "activities"} '
            "with $0 net obligations in FY${data.currentFY}`",
            children_card,
        )
        self.assertIn('el("details", { class: "detail-table" });', children_card)
        # The split happens after the main table is appended and only the
        # main table is appended unconditionally -- the details block is
        # gated on splitZeroRows.
        main_pos = children_card.index("card.append(buildTable(mainRows));")
        details_pos = children_card.index("if (splitZeroRows) {")
        self.assertLess(main_pos, details_pos)


if __name__ == "__main__":
    unittest.main()
