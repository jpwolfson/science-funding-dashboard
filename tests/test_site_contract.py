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
                     "Appropriations obligation dashboards",
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
            "science-related federal accounts, including defense RDT&E.`",
            self.html,
        )
        self.assertIn(
            "Obligations from ${fmtN(obligationSummary.accountCount ?? 0)} "
            "registered science-related federal accounts, including "
            "defense RDT&E.",
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
            "renderDataQualityNotes(data.dataQualityNotes)",
            'id: "methodologyNote"',
            'id: "dataQualityNotes"',
        ):
            self.assertIn(text, self.html)
        # dataQualityNotes must not render through the red warnings banner.
        methodology_block = self.html.split(
            "function renderDataQualityNotes(notes) {", 1
        )[1].split("function renderMethodologyNote", 1)[0]
        self.assertNotIn('class: "banner"', methodology_block)

    def test_award_root_has_parallel_obligation_summary_tiles(self):
        for text in ('heading: "Award activity"',
                     'heading: `${obligationScope} obligations`',
                     "obligationTiles(obligationSummary",
                     "compact: true",
                     "not additive to, the award totals above",
                     "not new awards",
                     "sign alone does not establish a cancellation"):
            self.assertIn(text, self.html)

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
        self.assertIn("function episodeHeadingText(episode) {", self.html)
        self.assertIn('el("h2", { text: episodeHeadingText(episode) })', self.html)
        # The old pattern that rendered a raw episode.title as the card
        # heading must not reappear.
        self.assertNotIn('el("h2", { text: episode.title', self.html)

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


if __name__ == "__main__":
    unittest.main()
