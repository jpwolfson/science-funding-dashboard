import unittest
from pathlib import Path


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
                     "not overdue", "gross negative activity",
                     "net activity", "Attributed source headline",
                     "Optional review finding"):
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
            "attributedText(event.statedReason, source, { omitCitation: true })",
            "attributedText(announcedDisplay, source, { omitCitation: true })",
            "attributedText(first.sourceTitle || first.sourceId, source, { omitCitation: true })",
            "attributedText(null, source)",
        ):
            self.assertIn(text, self.html)
        # Forbidden: the same fields must never be interpolated directly into
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
