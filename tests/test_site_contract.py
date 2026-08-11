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
                     "File C is award-linked enrichment",
                     "publicUSAspendingAwardUrl(flow.awardUrl)"):
            self.assertIn(text, self.html)


if __name__ == "__main__":
    unittest.main()
