import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from pathlib import Path

from scripts.assemble_pages_site import (
    assemble_pages_site,
    assembled_content_contract,
    excluded_from_pages,
    pages_source_summary,
    rendered_link_problems,
)
from scripts.check_pages_footprint import classify, main, measure_tree, report


REPO = Path(__file__).resolve().parent.parent


class PagesFootprintTests(unittest.TestCase):
    def fixture(self, root):
        (root / "site").mkdir()
        (root / "site" / "index.html").write_bytes(b"index")
        events = root / "data" / "obligations" / "agency" / "account" / "events"
        events.mkdir(parents=True)
        (events / "FY2025.csv.gz").write_bytes(b"audit-only")
        (events / "FY2025.provenance.json").write_bytes(b"provenance")
        (events / "manifest.json").write_bytes(b"manifest")
        (root / "data" / "obligations" / "dashboard.json").write_bytes(b"runtime")
        (root / "data" / "other.csv.gz").write_bytes(b"runtime-gzip")
        nsf = root / "data" / "nsf" / "directorate" / "division"
        nsf.mkdir(parents=True)
        (nsf / "awards.csv").write_bytes(b"nsf-runtime-download")

    def test_assembler_excludes_only_obligation_event_csv_archives(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            output = root / "artifact"
            assembled = assemble_pages_site(root, output)
            self.assertFalse(
                (output / "data/obligations/agency/account/events/FY2025.csv.gz").exists()
            )
            self.assertTrue(
                (output / "data/obligations/agency/account/events/FY2025.provenance.json").exists()
            )
            self.assertTrue(
                (output / "data/obligations/agency/account/events/manifest.json").exists()
            )
            self.assertTrue((output / "data/other.csv.gz").exists())
            self.assertTrue(
                (output / "data/nsf/directorate/division/awards.csv").is_file()
            )
            source = pages_source_summary(root)
            self.assertEqual(source["fileCount"], assembled["fileCount"])
            self.assertEqual(source["totalBytes"], assembled["totalBytes"])
            self.assertEqual(
                {"fileCount": assembled["fileCount"],
                 "totalBytes": assembled["totalBytes"]},
                measure_tree(output),
            )
            self.assertEqual({
                "nsfAwardCsvSourceCount": 1,
                "nsfAwardCsvArtifactCount": 1,
                "obligationEventArchiveSourceCount": 1,
                "obligationEventArchiveArtifactCount": 0,
            }, assembled_content_contract(root, output))

    def test_exclusion_is_narrow_and_path_aware(self):
        self.assertTrue(excluded_from_pages(
            "data/obligations/agency/account/events/FY2025.csv.gz"
        ))
        self.assertFalse(excluded_from_pages(
            "data/obligations/agency/account/events/FY2025.provenance.json"
        ))
        self.assertFalse(excluded_from_pages("data/other.csv.gz"))

    def test_threshold_boundaries_warn_then_stop(self):
        self.assertEqual("ok", classify(849_999_999))
        self.assertEqual("warning", classify(850_000_000))
        self.assertEqual("warning", classify(949_999_999))
        self.assertEqual("stop", classify(950_000_000))

    def test_report_exposes_exact_headroom(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            self.fixture(repo)
            artifact = root / "artifact"
            assemble_pages_site(repo, artifact)
            result = report(artifact, repo=repo)
            self.assertEqual(measure_tree(artifact)["totalBytes"], result["totalBytes"])
            self.assertEqual(
                1_000_000_000 - result["totalBytes"], result["headroomBytes"]
            )
            self.assertEqual("ok", result["status"])

    def test_rendered_links_resolve_only_against_assembled_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            self.fixture(repo)
            artifact = Path(temporary) / "artifact"
            assemble_pages_site(repo, artifact)
            good = [
                "index.html?org=nsf/directorate/division",
                "data/nsf/directorate/division/awards.csv",
                "https://github.com/jpwolfson/science-funding-dashboard/blob/main/"
                "data/obligations/agency/account/events/FY2025.csv.gz",
            ]
            self.assertEqual([], rendered_link_problems(good, artifact))
            relative_archive = (
                "data/obligations/agency/account/events/FY2025.csv.gz"
            )
            problems = rendered_link_problems([relative_archive], artifact)
            self.assertEqual(1, len(problems))
            self.assertIn("Pages-relative instead of github.com", problems[0])
            problems = rendered_link_problems(
                ["data/nsf/directorate/division/missing.csv"], artifact
            )
            self.assertEqual(1, len(problems))
            self.assertIn("missing from assembled artifact", problems[0])

    def test_warning_surfaces_in_actions_annotation_and_job_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            self.fixture(repo)
            artifact = Path(temporary) / "artifact"
            assemble_pages_site(repo, artifact)
            total = measure_tree(artifact)["totalBytes"]
            summary = Path(temporary) / "summary.md"
            report_json = Path(temporary) / "report.json"
            stdout = StringIO()
            with patch.dict("os.environ", {
                "GITHUB_ACTIONS": "true",
                "GITHUB_STEP_SUMMARY": str(summary),
            }, clear=False), redirect_stdout(stdout):
                code = main([
                    "--repo", str(repo),
                    "--site-root", str(artifact),
                    "--warning-bytes", str(total),
                    "--stop-bytes", str(total + 1),
                    "--json", str(report_json),
                ])
            self.assertEqual(0, code)
            self.assertIn("::warning title=GitHub Pages footprint::", stdout.getvalue())
            summary_text = summary.read_text()
            self.assertIn("**Status:** warning", summary_text)
            self.assertIn(f"**Assembled artifact:** {total} bytes", summary_text)
            payload = __import__("json").loads(report_json.read_text())
            self.assertEqual(total, payload["totalBytes"])

    def test_every_pages_workflow_assembles_minimal_site_then_gates_it(self):
        for relative in (
            ".github/workflows/deploy-pages.yml",
            ".github/workflows/update-data.yml",
            ".github/workflows/update-obligations.yml",
        ):
            text = (REPO / relative).read_text()
            assemble = text.index("python scripts/assemble_pages_site.py")
            gate = text.index("python scripts/check_pages_footprint.py")
            upload = text.index("actions/upload-pages-artifact@v3")
            self.assertLess(assemble, gate, relative)
            self.assertLess(gate, upload, relative)
            self.assertNotIn("cp -r data", text, relative)

    def test_runtime_shell_never_references_excluded_event_archives(self):
        shell = (REPO / "site" / "index.html").read_text()
        self.assertNotIn(".csv.gz", shell)
        self.assertNotIn("/events/", shell)


if __name__ == "__main__":
    unittest.main()
