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
        for text in ("renderViewNav(obligationRoot)",
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


if __name__ == "__main__":
    unittest.main()
