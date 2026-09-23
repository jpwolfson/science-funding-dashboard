import http.client
import io
import json
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch

from adapters.obligation_common import (
    account_period_status, apply_dollar_transient_rule, classify_file_b_periods,
    fy_cumulative_cents, load_store, normalize_event, period_info,
)
from adapters.usaspending_obligations import (
    DOWNLOAD_STATUS_TIMEOUT_SECONDS,
    _bytes, _download_request_payload, _json, alias_map,
    combine_file_b_file_c, file_b_period_events,
    finish_download, resume_download,
    parse_file_b_snapshot, parse_file_c,
)
from scripts.pull_obligation_account import (
    FILE_B_COLUMNS, _baseline_pin, _download,
    _load_resume_handoffs, _resume_handoff_matches_run, _resume_request,
    _validate_account_total, _write_resume_handoff, pull, run_identity_from_environ,
)


ALIASES = {"0001": {"code": "0001", "name": "BES", "park": "PARK1"},
           "PARK1": {"code": "0001", "name": "BES", "park": "PARK1"},
           "0000": {"code": "0000", "name": "Unknown / other", "park": ""}}


def _echoed_download_request(account_id, fy, period, kind, columns):
    """Build the accepted-scope shape USAspending echoes back, exactly as
    ``_validate_download_result`` expects it (distinct from this repo's
    outgoing request payload shape)."""
    payload = _download_request_payload(account_id, fy, period, kind, columns)
    return {
        "account_level": payload["account_level"],
        "file_format": payload["file_format"],
        "columns": payload["columns"],
        "download_types": payload["filters"]["submission_types"],
        "filters": {
            "federal_account": payload["filters"]["federal_account"],
            "fy": payload["filters"]["fy"],
            "period": payload["filters"]["period"],
        },
    }


class USAspendingObligationTests(unittest.TestCase):
    def test_dual_exact_pin_preserves_file_a_and_file_b_semantics(self):
        account = {
            "path": "agency/account",
            "federalAccount": "999-0001",
            "baseline": "reference/account.json",
            "availability": {"firstFiscalYear": 2017,
                             "firstFiscalYearPeriod": 6},
        }
        pin = {
            "status": "complete",
            "obligationsCents": 101,
            "fileBObligationsCents": 100,
            "fileAFileBVarianceCents": 1,
            "fileAFileBVarianceReason": "Official source warning A19",
        }
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / "reference"
            reference.mkdir()
            (reference / "account.json").write_text(json.dumps({
                "schemaVersion": 2,
                "federalAccount": "999-0001",
                "fiscalYears": {"2024": pin},
            }))
            self.assertEqual(
                pin, _baseline_pin(Path(temp), account, 2024, 12, 100)
            )
            _validate_account_total(2024, 12, 101, 100, pin)
            _validate_account_total(2024, 12, 100, 100, pin)
            with self.assertRaisesRegex(
                    ValueError, "pinned File A 101 or pinned File B 100"):
                _validate_account_total(2024, 12, 102, 100, pin)
            with self.assertRaisesRegex(ValueError, "pinned File B"):
                _validate_account_total(2024, 12, 101, 99, pin)
            with self.assertRaisesRegex(ValueError, "pinned File B"):
                _baseline_pin(Path(temp), account, 2024, 12, 99)

            partial = dict(pin, status="partial", asOfPeriod=9,
                           firstPeriod=2)
            value = json.loads((reference / "account.json").read_text())
            value["fiscalYears"]["2024"] = partial
            (reference / "account.json").write_text(json.dumps(value))
            self.assertEqual(
                partial, _baseline_pin(Path(temp), account, 2024, 9, 100)
            )
            with self.assertRaisesRegex(ValueError, "as-of P09"):
                _baseline_pin(Path(temp), account, 2024, 10, 100)

    def test_baseline_pin_refuses_to_advance_onto_a_zero_collapse(self):
        # The ed/ies FY2026 P10 regression: a prior partial pin was
        # positive, and the newly computed File B total collapsed to
        # exactly zero cents. The pin must not advance; the last accepted
        # pin is kept unchanged.
        account = {
            "path": "ed/ies", "federalAccount": "091-0300",
            "baseline": "reference/account.json",
            "availability": {"firstFiscalYear": 2017, "firstFiscalYearPeriod": 6},
        }
        old_pin = {"status": "partial", "asOfPeriod": 9, "obligationsCents": 500}
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / "reference"
            reference.mkdir()
            (reference / "account.json").write_text(json.dumps({
                "schemaVersion": 2, "federalAccount": "091-0300",
                "fiscalYears": {"2026": old_pin},
            }))
            self.assertEqual(
                old_pin, _baseline_pin(Path(temp), account, 2026, 10, 0)
            )

    def test_multiple_historical_parks_normalize_to_one_canonical_activity(self):
        aliases = alias_map({"programActivities": [{
            "slug": "research", "code": "0001", "name": "Research",
            "park": "CURRENT", "parkAliases": ["HISTORICAL-A", "HISTORICAL-B"],
        }]})
        values = parse_file_b_snapshot([{
            "federal_account_symbol": "999-0001",
            "program_activity_reporting_key": "HISTORICAL-A",
            "program_activity_name": "Old research label",
            "obligations_incurred": "1.00",
        }], "999-0001", aliases)
        self.assertEqual({("0001", "0001", "Research", "CURRENT",
                           "", "", "", ""): 100},
                         values)

    def test_one_park_cannot_alias_multiple_canonical_activities(self):
        with self.assertRaisesRegex(ValueError, "maps to multiple identities"):
            alias_map({"programActivities": [
                {"slug": "first", "code": "0001", "name": "First",
                 "park": "SHARED"},
                {"slug": "second", "code": "0002", "name": "Second",
                 "parkAliases": ["SHARED"]},
            ]})

    def test_reused_code_is_disambiguated_by_exact_name(self):
        aliases = alias_map({"programActivities": [
            {"slug": "spectrum", "code": "0010",
             "name": "Spectrum Relocation Fund"},
            {"slug": "omao", "code": "0010", "name": "OMAO",
             "codeNameAliases": [
                 {"code": "0007", "name": "Office of Marine and Aviation Operations"},
             ]},
        ]})
        values = parse_file_b_snapshot([
            {"federal_account_symbol": "013-1450",
             "program_activity_code": "0010",
             "program_activity_name": "Spectrum Relocation Fund",
             "obligations_incurred": "1.00"},
            {"federal_account_symbol": "013-1450",
             "program_activity_code": "0010",
             "program_activity_name": "OMAO",
             "obligations_incurred": "2.00"},
        ], "013-1450", aliases)
        identities = {(key[0], key[1], key[2]): amount
                      for key, amount in values.items()}
        self.assertEqual({
            ("0010:spectrum", "0010", "Spectrum Relocation Fund"): 100,
            ("0010:omao", "0010", "OMAO"): 200,
        }, identities)
        flows = file_b_period_events({"FY2024P02": values}, "013-1450")
        events = combine_file_b_file_c(flows, [], "013-1450")
        self.assertEqual(300, sum(row["amountCents"] for row in events))
        self.assertEqual(2, len({row["id"] for row in events}))
        self.assertEqual({"OMAO", "Spectrum Relocation Fund"},
                         {row["programActivityName"] for row in events})

    def test_unmapped_nonblank_program_activity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-0222",
                "program_activity_code": "0099",
                "program_activity_name": "New unmapped activity",
                "obligations_incurred": "1.00",
            }], "089-0222", ALIASES)

    def test_unmapped_park_with_blank_legacy_fields_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-2250",
                "program_activity_reporting_key": "NEW-PARK",
                "program_activity_code": "",
                "program_activity_name": "",
                "obligations_incurred": "1.00",
            }], "089-2250", ALIASES)

    def test_unmapped_park_does_not_fall_through_to_known_legacy_code(self):
        with self.assertRaisesRegex(ValueError, "unmapped Program Activity"):
            parse_file_b_snapshot([{
                "federal_account_symbol": "089-0222",
                "program_activity_reporting_key": "NEW-PARK",
                "program_activity_code": "0001",
                "program_activity_name": "BES",
                "obligations_incurred": "1.00",
            }], "089-0222", ALIASES)

    def test_remote_disconnect_is_retried(self):
        response = io.BytesIO(b'{"ok": true}')
        with patch(
                "adapters.usaspending_obligations.urllib.request.urlopen",
                side_effect=[http.client.RemoteDisconnected(), response]) as open_, \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            self.assertEqual(_json("https://example.test", attempts=2), {"ok": True})
        self.assertEqual(open_.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_not_found_still_fails_immediately_by_default(self):
        error = urllib.error.HTTPError(
            "https://example.test", 404, "Not Found", {}, None)
        with patch(
                "adapters.usaspending_obligations.urllib.request.urlopen",
                side_effect=error) as open_, \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            with self.assertRaises(urllib.error.HTTPError):
                _json("https://example.test", attempts=2)
        self.assertEqual(open_.call_count, 1)
        sleep.assert_not_called()

    def test_download_status_not_found_is_retried(self):
        error = urllib.error.HTTPError(
            "https://api.usaspending.gov/api/v2/download/status/1",
            404, "Not Found", {}, None)
        finished = io.BytesIO(
            b'{"status":"finished","file_url":'
            b'"https://files.usaspending.gov/archive.zip"}')
        with patch(
                "adapters.usaspending_obligations.urllib.request.urlopen",
                side_effect=[error, finished]) as open_, \
             patch("adapters.usaspending_obligations._bytes",
                   return_value=b"archive") as archive, \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            payload, status = finish_download({
                "status_url": "/api/v2/download/status/1",
            })
        self.assertEqual(b"archive", payload)
        self.assertEqual("finished", status["status"])
        self.assertEqual(open_.call_count, 2)
        sleep.assert_called_once_with(1)
        archive.assert_called_once_with(
            "https://files.usaspending.gov/archive.zip")

    def test_download_status_default_outlasts_one_hour_build(self):
        running = {"status": "running"}
        finished = {
            "status": "finished",
            "file_url": "https://files.usaspending.gov/archive.zip",
        }
        with patch(
                "adapters.usaspending_obligations._json",
                side_effect=[running, finished]) as status, \
             patch("adapters.usaspending_obligations._bytes",
                   return_value=b"archive") as archive, \
             patch("adapters.usaspending_obligations.time.monotonic",
                   side_effect=[100, 100 + 3601, 100 + 3602]), \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            payload, observed = finish_download({
                "status_url": "/api/v2/download/status/slow",
            })
        self.assertEqual(7200, DOWNLOAD_STATUS_TIMEOUT_SECONDS)
        self.assertEqual(b"archive", payload)
        self.assertIs(finished, observed)
        self.assertEqual(2, status.call_count)
        sleep.assert_called_once_with(15)
        archive.assert_called_once_with(
            "https://files.usaspending.gov/archive.zip")

    def test_resume_download_requires_exact_accepted_scope(self):
        result = {
            "status_url": (
                "https://api.usaspending.gov/api/v2/download/status?"
                "file_name=accepted.zip"
            ),
            "download_request": {
                "account_level": "federal_account",
                "file_format": "csv",
                "columns": FILE_B_COLUMNS,
                "download_types": ["object_class_program_activity"],
                "filters": {
                    "federal_account": "5787",
                    "fy": 2023,
                    "period": 2,
                },
            },
        }
        observed, scope = resume_download(
            "5787", 2023, 2, "object_class_program_activity",
            FILE_B_COLUMNS, result,
        )
        self.assertIs(result, observed)
        self.assertEqual("5787", scope["filters"]["federal_account"])
        mismatched = json.loads(json.dumps(result))
        mismatched["download_request"]["filters"]["period"] = 3
        with self.assertRaisesRegex(ValueError, "different request scope"):
            resume_download(
                "5787", 2023, 2, "object_class_program_activity",
                FILE_B_COLUMNS, mismatched,
            )
        unexpected_host = json.loads(json.dumps(result))
        unexpected_host["status_url"] = "https://example.test/status"
        with self.assertRaisesRegex(ValueError, "unexpected download status"):
            resume_download(
                "5787", 2023, 2, "object_class_program_activity",
                FILE_B_COLUMNS, unexpected_host,
            )

    def test_resume_manifest_selects_only_the_exact_pull(self):
        result = {"status_url": "https://api.usaspending.gov/status"}
        manifest = {
            "schemaVersion": 1,
            "requests": [{
                "account": "doe/nnsa-weapons-activities",
                "fiscalYear": 2023,
                "period": 2,
                "submissionType": "object_class_program_activity",
                "result": result,
            }],
        }
        account = {"path": "doe/nnsa-weapons-activities"}
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / "reference"
            reference.mkdir()
            (reference / "obligation_download_resumes.json").write_text(
                json.dumps(manifest)
            )
            with patch(
                "scripts.pull_obligation_account.resume_download",
                return_value=("accepted", "scope"),
            ) as resume:
                self.assertEqual(
                    ("accepted", "scope"),
                    _resume_request(
                        temp, account, "5787", 2023, 2,
                        "object_class_program_activity", FILE_B_COLUMNS,
                    ),
                )
                self.assertIsNone(_resume_request(
                    temp, account, "5787", 2023, 3,
                    "object_class_program_activity", FILE_B_COLUMNS,
                ))
            resume.assert_called_once_with(
                "5787", 2023, 2, "object_class_program_activity",
                FILE_B_COLUMNS, result,
            )

    def test_timeout_retains_exact_resume_handoff_in_raw_artifact(self):
        account = {"path": "commerce/bea"}
        request = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/slow",
            "download_request": {"filters": {"fy": 2018, "period": 12}},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(request, {"requested": True})), \
             patch("scripts.pull_obligation_account.finish_download",
                   side_effect=TimeoutError("still running")):
            with self.assertRaisesRegex(TimeoutError, "still running"):
                _download(
                    temp, account, "3693", 2018, 12,
                    "award_financial", FILE_B_COLUMNS,
                    raw_archive_dir=temp,
                )
            handoffs = list(Path(temp).glob("obligation-download-resume-*.json"))
            self.assertEqual(1, len(handoffs))
            self.assertEqual({
                "schemaVersion": 1,
                "requests": [{
                    "account": "commerce/bea",
                    "fiscalYear": 2018,
                    "period": 12,
                    "submissionType": "award_financial",
                    "result": request,
                }],
            }, json.loads(handoffs[0].read_text()))

    def test_finished_download_replaces_handoff_with_raw_archive(self):
        account = {"path": "commerce/bea"}
        request = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/done",
            "download_request": {"filters": {"fy": 2018, "period": 12}},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(request, {"requested": True})), \
             patch("scripts.pull_obligation_account.finish_download",
                   return_value=(b"archive", {"status": "finished",
                                              "total_rows": 0})), \
             patch("scripts.pull_obligation_account.archive_rows",
                   return_value={}):
            members, audit = _download(
                temp, account, "3693", 2018, 12,
                "award_financial", FILE_B_COLUMNS,
                raw_archive_dir=temp,
            )
            self.assertEqual({}, members)
            self.assertEqual(0, audit["parsedRowCount"])
            self.assertEqual([], list(Path(temp).glob(
                "obligation-download-resume-*.json"
            )))
            self.assertEqual(1, len(list(Path(temp).glob("*.zip"))))

    def test_source_rejected_download_clears_resume_handoff(self):
        account = {"path": "commerce/bea"}
        request = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/failed",
            "download_request": {"filters": {"fy": 2018, "period": 12}},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(request, {"requested": True})), \
             patch("scripts.pull_obligation_account.finish_download",
                   side_effect=ValueError("source download failed")):
            with self.assertRaisesRegex(ValueError, "source download failed"):
                _download(
                    temp, account, "3693", 2018, 12,
                    "award_financial", FILE_B_COLUMNS,
                    raw_archive_dir=temp,
                )
            self.assertEqual([], list(Path(temp).glob(
                "obligation-download-resume-*.json"
            )))

    def test_automatic_resume_finishes_without_a_fresh_request(self):
        # The adapter's own next-attempt handoff (as staged by the workflow
        # into _raw_previous) should be picked up and finished without ever
        # POSTing a new download request.
        account = {"path": "ed/ies"}
        result = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/resume",
            "download_request": _echoed_download_request(
                "5555", 2018, 2, "object_class_program_activity", FILE_B_COLUMNS
            ),
        }
        handoffs = {
            ("ed/ies", 2018, 2, "object_class_program_activity"): {
                "account": "ed/ies", "fiscalYear": 2018, "period": 2,
                "submissionType": "object_class_program_activity",
                "runId": "111", "headSha": "abc123", "result": result,
            },
        }
        run_identity = {"runId": "111", "headSha": "abc123"}
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account.request_download") as fresh, \
             patch("scripts.pull_obligation_account.finish_download",
                   return_value=(b"archive", {"status": "finished",
                                              "total_rows": 0})), \
             patch("scripts.pull_obligation_account.archive_rows",
                   return_value={}):
            members, audit = _download(
                temp, account, "5555", 2018, 2,
                "object_class_program_activity", FILE_B_COLUMNS,
                raw_archive_dir=temp, resume_handoffs=handoffs,
                run_identity=run_identity,
            )
        fresh.assert_not_called()
        self.assertEqual({}, members)
        self.assertEqual(0, audit["parsedRowCount"])

    def test_automatic_resume_falls_through_on_run_and_head_sha_mismatch(self):
        account = {"path": "ed/ies"}
        result = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/resume",
            "download_request": {"filters": {"fy": 2018, "period": 2}},
        }
        handoffs = {
            ("ed/ies", 2018, 2, "object_class_program_activity"): {
                "account": "ed/ies", "fiscalYear": 2018, "period": 2,
                "submissionType": "object_class_program_activity",
                "runId": "111", "headSha": "abc123", "result": result,
            },
        }
        # A different run AND a different head SHA: the handoff must never
        # be trusted, so a brand-new request is issued instead.
        run_identity = {"runId": "222", "headSha": "def456"}
        fresh_request = {"status_url": "https://api.usaspending.gov/status/fresh"}
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(fresh_request, {"requested": True})) as fresh, \
             patch("scripts.pull_obligation_account.finish_download",
                   return_value=(b"archive", {"status": "finished",
                                              "total_rows": 0})), \
             patch("scripts.pull_obligation_account.archive_rows",
                   return_value={}):
            _download(
                temp, account, "5555", 2018, 2,
                "object_class_program_activity", FILE_B_COLUMNS,
                raw_archive_dir=temp, resume_handoffs=handoffs,
                run_identity=run_identity,
            )
        fresh.assert_called_once()

    def test_automatic_resume_falls_through_when_source_declares_it_failed(self):
        account = {"path": "usda/nifa-research-education"}
        result = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/resume",
            "download_request": _echoed_download_request(
                "7777", 2019, 12, "award_financial", FILE_B_COLUMNS
            ),
        }
        handoffs = {
            ("usda/nifa-research-education", 2019, 12, "award_financial"): {
                "account": "usda/nifa-research-education", "fiscalYear": 2019,
                "period": 12, "submissionType": "award_financial",
                "runId": "999", "headSha": "sha999", "result": result,
            },
        }
        run_identity = {"runId": "999", "headSha": "sha999"}
        fresh_request = {"status_url": "https://api.usaspending.gov/status/fresh"}
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(fresh_request, {"requested": True})) as fresh, \
             patch("scripts.pull_obligation_account.finish_download",
                   side_effect=[
                       RuntimeError("custom-account download ended in 'failed'"),
                       (b"archive", {"status": "finished", "total_rows": 0}),
                   ]) as finish, \
             patch("scripts.pull_obligation_account.archive_rows",
                   return_value={}):
            members, audit = _download(
                temp, account, "7777", 2019, 12,
                "award_financial", FILE_B_COLUMNS,
                raw_archive_dir=temp, resume_handoffs=handoffs,
                run_identity=run_identity,
            )
        fresh.assert_called_once()
        self.assertEqual(2, finish.call_count)
        self.assertEqual({}, members)
        self.assertEqual(0, audit["parsedRowCount"])

    def test_automatic_resume_handoff_used_at_most_once(self):
        # A resumed request that times out again must not be retried
        # against the very same stale handoff -- only a fresh request is
        # attempted on the fallback.
        account = {"path": "ed/ies"}
        result = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/resume",
            "download_request": _echoed_download_request(
                "5555", 2018, 2, "object_class_program_activity", FILE_B_COLUMNS
            ),
        }
        handoffs = {
            ("ed/ies", 2018, 2, "object_class_program_activity"): {
                "account": "ed/ies", "fiscalYear": 2018, "period": 2,
                "submissionType": "object_class_program_activity",
                "runId": "111", "headSha": "abc", "result": result,
            },
        }
        run_identity = {"runId": "111", "headSha": "abc"}
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=({"status_url": "https://api.usaspending.gov/status/fresh"},
                                 {"requested": True})), \
             patch("scripts.pull_obligation_account.finish_download",
                   side_effect=[
                       RuntimeError("custom-account download ended in 'failed'"),
                       TimeoutError("still running"),
                   ]) as finish:
            with self.assertRaisesRegex(TimeoutError, "still running"):
                _download(
                    temp, account, "5555", 2018, 2,
                    "object_class_program_activity", FILE_B_COLUMNS,
                    raw_archive_dir=temp, resume_handoffs=handoffs,
                    run_identity=run_identity,
                )
            self.assertEqual(2, finish.call_count)
            # The one handoff on disk now describes the fresh request, not
            # the stale resumed one -- the next attempt will resume THAT.
            handoff_files = list(
                Path(temp).glob("obligation-download-resume-*.json")
            )
            self.assertEqual(1, len(handoff_files))
            written = json.loads(handoff_files[0].read_text())
            self.assertEqual(
                "https://api.usaspending.gov/status/fresh",
                written["requests"][0]["result"]["status_url"],
            )

    def test_write_resume_handoff_records_run_identity_when_known(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "handoff.json"
            _write_resume_handoff(
                path, {"path": "doe/sc"}, 2024, 6, "award_financial",
                {"status_url": "https://api.usaspending.gov/status/x"},
                run_identity={"runId": "123", "headSha": "deadbeef"},
            )
            row = json.loads(path.read_text())["requests"][0]
            self.assertEqual("123", row["runId"])
            self.assertEqual("deadbeef", row["headSha"])

            # Omitting run identity keeps the pre-existing exact shape, so
            # a manually authored reviewed handoff is unaffected.
            path.unlink()
            _write_resume_handoff(
                path, {"path": "doe/sc"}, 2024, 6, "award_financial",
                {"status_url": "https://api.usaspending.gov/status/x"},
            )
            row = json.loads(path.read_text())["requests"][0]
            self.assertNotIn("runId", row)
            self.assertNotIn("headSha", row)

    def test_handoff_survives_a_non_valueerror_interruption(self):
        # The job-timeout kill signal surfaces as something other than the
        # adapter's own ValueError (e.g. TimeoutError, or KeyboardInterrupt
        # if the process is killed mid-poll); only the ValueError branch
        # ever clears a handoff, so the in-flight request's handoff must
        # still be on disk after any other interruption.
        account = {"path": "commerce/bea"}
        request = {
            "status_url": "https://api.usaspending.gov/api/v2/download/status/slow",
            "download_request": {"filters": {"fy": 2018, "period": 12}},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch("scripts.pull_obligation_account._resume_request",
                   return_value=None), \
             patch("scripts.pull_obligation_account.request_download",
                   return_value=(request, {"requested": True})), \
             patch("scripts.pull_obligation_account.finish_download",
                   side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                _download(
                    temp, account, "3693", 2018, 12,
                    "award_financial", FILE_B_COLUMNS,
                    raw_archive_dir=temp,
                )
            handoffs = list(Path(temp).glob("obligation-download-resume-*.json"))
            self.assertEqual(1, len(handoffs))

    def test_load_resume_handoffs_unions_files_and_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "obligation-download-resume-a.json").write_text(json.dumps({
                "schemaVersion": 1,
                "requests": [{"account": "doe/sc", "fiscalYear": 2024,
                              "period": 2, "submissionType": "award_financial",
                              "result": {"status_url": "x"}}],
            }))
            (directory / "obligation-download-resume-b.json").write_text(json.dumps({
                "schemaVersion": 1,
                "requests": [{"account": "doe/sc", "fiscalYear": 2024,
                              "period": 3, "submissionType": "award_financial",
                              "result": {"status_url": "y"}}],
            }))
            handoffs = _load_resume_handoffs(directory)
            self.assertEqual(2, len(handoffs))
            self.assertIn(("doe/sc", 2024, 2, "award_financial"), handoffs)
            self.assertIn(("doe/sc", 2024, 3, "award_financial"), handoffs)

            (directory / "obligation-download-resume-c.json").write_text(json.dumps({
                "schemaVersion": 1,
                "requests": [{"account": "doe/sc", "fiscalYear": 2024,
                              "period": 2, "submissionType": "award_financial",
                              "result": {"status_url": "z"}}],
            }))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                _load_resume_handoffs(directory)

    def test_load_resume_handoffs_is_empty_when_directory_is_absent(self):
        self.assertEqual({}, _load_resume_handoffs("/no/such/directory"))

    def test_resume_handoff_match_rules(self):
        account = {"path": "ed/ies"}
        same_run = {"runId": "1", "headSha": "a", "account": "ed/ies",
                    "fiscalYear": 2018}
        # No run-identity context (e.g. local/offline use): always trusted.
        self.assertTrue(
            _resume_handoff_matches_run(same_run, None, account, 2018)
        )
        # Same run ID: trusted regardless of head SHA bookkeeping.
        self.assertTrue(_resume_handoff_matches_run(
            same_run, {"runId": "1", "headSha": "different"}, account, 2018
        ))
        # Different run, but matching head SHA and account/FY scope.
        cross_run = {"runId": "1", "headSha": "a", "account": "ed/ies",
                     "fiscalYear": 2018}
        self.assertTrue(_resume_handoff_matches_run(
            cross_run, {"runId": "2", "headSha": "a"}, account, 2018
        ))
        # Different run and different head SHA: rejected.
        self.assertFalse(_resume_handoff_matches_run(
            cross_run, {"runId": "2", "headSha": "b"}, account, 2018
        ))
        # Different run, matching head SHA, but different account: rejected.
        self.assertFalse(_resume_handoff_matches_run(
            cross_run, {"runId": "2", "headSha": "a"},
            {"path": "ed/other"}, 2018
        ))
        # A handoff with no recorded run identity is never trusted across
        # runs, even if the caller's run identity happens to have a head
        # SHA -- fail closed rather than assume compatibility.
        legacy = {"account": "ed/ies", "fiscalYear": 2018}
        self.assertFalse(_resume_handoff_matches_run(
            legacy, {"runId": "2", "headSha": "a"}, account, 2018
        ))

    def test_run_identity_from_environ(self):
        self.assertIsNone(run_identity_from_environ({}))
        self.assertEqual(
            {"runId": "42", "headSha": "abc"},
            run_identity_from_environ(
                {"GITHUB_RUN_ID": "42", "GITHUB_SHA": "abc"}
            ),
        )

    def test_archive_download_outlasts_six_disconnects(self):
        response = io.BytesIO(b"archive")
        with patch(
                "adapters.usaspending_obligations.urllib.request.urlopen",
                side_effect=[http.client.RemoteDisconnected()] * 6
                            + [response]) as open_, \
             patch("adapters.usaspending_obligations.time.sleep") as sleep:
            self.assertEqual(_bytes("https://files.usaspending.gov/a.zip"),
                             b"archive")
        self.assertEqual(open_.call_count, 7)
        self.assertEqual([1, 2, 4, 8, 16, 32],
                         [call.args[0] for call in sleep.call_args_list])

    def test_file_b_cumulative_snapshots_are_differenced(self):
        key = ("0001", "0001", "BES", "PARK1", "25.1", "D", "", "")
        vanished = ("0001", "0001", "BES", "PARK1", "25.2", "D", "", "")
        flows = file_b_period_events({"FY2024P02": {key: 100, vanished: 50},
                                      "FY2024P03": {key: 130}}, "089-0222")
        self.assertEqual([150, -20], [row["amountCents"] for row in flows])

    def test_file_c_hidden_dimensions_collapse_without_rounding(self):
        base = {"submission_period": "FY2024P02", "federal_account_symbol": "089-0222",
                "program_activity_code": "0001", "program_activity_name": "BES",
                "award_unique_key": "A", "recipient_name": "Lab"}
        parts = {"Assistance.csv": [{**base, "transaction_obligated_amount": "1.25"},
                                     {**base, "transaction_obligated_amount": "-0.25"}],
                 "Contracts.csv": [], "Unlinked.csv": []}
        events = parse_file_c(parts, "089-0222", ALIASES)
        self.assertEqual(1, len(events))
        self.assertEqual(100, events[0]["amountCents"])
        self.assertEqual(2, events[0]["sourceRowCount"])
        self.assertEqual(-25, events[0]["grossNegativeCents"])

    def test_residual_makes_file_b_exact(self):
        c_parts = {"Assistance.csv": [{"submission_period": "FY2024P02",
            "federal_account_symbol": "089-0222", "program_activity_code": "0001",
            "program_activity_name": "BES", "award_unique_key": "A",
            "transaction_obligated_amount": "7.00"}], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        b = [{"submissionPeriod": "FY2024P02", "federalAccount": "089-0222",
              "programActivityCode": "0001", "programActivityName": "BES",
              "programActivityReportingKey": "PARK1", "amountCents": 1000}]
        both = combine_file_b_file_c(b, c, "089-0222")
        self.assertEqual(1000, sum(e["amountCents"] for e in both))
        self.assertEqual(300, next(e["amountCents"] for e in both if e["source"] == "file_b_residual"))

    def test_unknown_file_c_bucket_without_file_b_anchor_nets_to_zero(self):
        c_parts = {"Assistance.csv": [{
            "submission_period": "FY2020P03",
            "federal_account_symbol": "089-0222",
            "program_activity_code": "",
            "program_activity_name": "",
            "award_unique_key": "A",
            "transaction_obligated_amount": "7.00",
        }], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        both = combine_file_b_file_c([], c, "089-0222")
        self.assertEqual(0, sum(e["amountCents"] for e in both))
        self.assertEqual(["0000", "0000"],
                         [e["programActivityCode"] for e in both])
        self.assertEqual(-700, next(
            e["amountCents"] for e in both
            if e["source"] == "file_b_residual"))

    def test_known_file_c_bucket_without_file_b_anchor_still_fails(self):
        c_parts = {"Assistance.csv": [{
            "submission_period": "FY2020P03",
            "federal_account_symbol": "089-0222",
            "program_activity_code": "0001",
            "program_activity_name": "BES",
            "award_unique_key": "A",
            "transaction_obligated_amount": "7.00",
        }], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        with self.assertRaisesRegex(ValueError, "absent from File B"):
            combine_file_b_file_c([], c, "089-0222")

    def test_quarterly_file_c_joins_period_ending_file_b(self):
        parts = {"Assistance.csv": [{"submission_period": "FY2017Q2",
            "federal_account_symbol": "089-0222", "program_activity_code": "0001",
            "program_activity_name": "BES", "award_unique_key": "A",
            "transaction_obligated_amount": "1.00"}], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(parts, "089-0222", ALIASES)
        self.assertEqual("FY2017P06", c[0]["submissionPeriod"])

    def test_not_reported_period_is_skipped_as_a_diff_boundary(self):
        # Navy RDT&E FY2025 shape: P02..P10 build normally, P11 returns an
        # anomalous single row (notReported), P12 recovers. The P12 delta
        # must be measured against the last *reported* snapshot (P10), not
        # against the near-empty P11 snapshot -- otherwise P11 shows a
        # fabricated multi-billion-dollar collapse and P12 an equal spike.
        key = ("0001", "0001", "BES", "PARK1", "", "", "", "")
        snapshots = {
            "FY2025P10": {key: 23_000_000_00},
            "FY2025P11": {key: 100},  # anomalous near-empty snapshot
            "FY2025P12": {key: 24_300_000_00},
        }
        row_counts = {"FY2025P10": 228, "FY2025P11": 1, "FY2025P12": 243}
        status = classify_file_b_periods(row_counts)
        self.assertEqual(
            {"FY2025P10": "reported", "FY2025P11": "notReported",
             "FY2025P12": "reported"}, status)
        flows = file_b_period_events(snapshots, "017-1319", status)
        # No flow at all for the notReported P11; the P12 span delta is
        # measured against the last reported snapshot, P10.
        self.assertEqual(["FY2025P10", "FY2025P12"],
                         [f["submissionPeriod"] for f in flows])
        by_period = {f["submissionPeriod"]: f["amountCents"] for f in flows}
        self.assertEqual(1_300_000_00, by_period["FY2025P12"])

    def test_file_c_in_a_not_reported_period_reconciles_at_the_covering_period(self):
        status = {"FY2024P02": "reported", "FY2024P03": "notReported",
                  "FY2024P04": "reported"}
        c_parts = {"Assistance.csv": [
            {"submission_period": "FY2024P02", "federal_account_symbol": "089-0222",
             "program_activity_code": "0001", "program_activity_name": "BES",
             "award_unique_key": "A", "transaction_obligated_amount": "5.00"},
            # File C activity dated inside the notReported period: it keeps
            # its own period label but is not reconciled until P04.
            {"submission_period": "FY2024P03", "federal_account_symbol": "089-0222",
             "program_activity_code": "0001", "program_activity_name": "BES",
             "award_unique_key": "B", "transaction_obligated_amount": "2.00"},
            {"submission_period": "FY2024P04", "federal_account_symbol": "089-0222",
             "program_activity_code": "0001", "program_activity_name": "BES",
             "award_unique_key": "C", "transaction_obligated_amount": "1.00"},
        ], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        b = [
            {"submissionPeriod": "FY2024P02", "federalAccount": "089-0222",
             "programActivityCode": "0001", "programActivityName": "BES",
             "programActivityReportingKey": "PARK1", "amountCents": 500},
            # P03 (notReported) has no File B flow at all.
            {"submissionPeriod": "FY2024P04", "federalAccount": "089-0222",
             "programActivityCode": "0001", "programActivityName": "BES",
             "programActivityReportingKey": "PARK1", "amountCents": 400},
        ]
        combined = combine_file_b_file_c(b, c, "089-0222", status)
        # File C events keep their own submission period unchanged.
        self.assertEqual(
            {"FY2024P02", "FY2024P03", "FY2024P04"},
            {e["submissionPeriod"] for e in combined if e["source"] == "file_c"})
        # No residual is booked for the notReported period itself.
        residuals = {e["submissionPeriod"]: e["amountCents"]
                     for e in combined if e["source"] == "file_b_residual"}
        self.assertNotIn("FY2024P03", residuals)
        # The P04 residual absorbs the whole span: 400 (P04 File B) minus
        # (200 P03 File C + 100 P04 File C) = 100.
        self.assertEqual(100, residuals["FY2024P04"])
        self.assertEqual(500 + 400, sum(e["amountCents"] for e in combined))

    def test_dangling_not_reported_tail_leaves_file_c_unmatched(self):
        # The most recently pulled period is itself notReported with no
        # later period fetched yet: its File C dollars stay unreconciled
        # until a future pull supplies the covering reported period.
        status = {"FY2024P02": "reported", "FY2024P03": "notReported"}
        c_parts = {"Assistance.csv": [
            {"submission_period": "FY2024P03", "federal_account_symbol": "089-0222",
             "program_activity_code": "0001", "program_activity_name": "BES",
             "award_unique_key": "A", "transaction_obligated_amount": "9.00"},
        ], "Contracts.csv": [], "Unlinked.csv": []}
        c = parse_file_c(c_parts, "089-0222", ALIASES)
        b = [{"submissionPeriod": "FY2024P02", "federalAccount": "089-0222",
              "programActivityCode": "0001", "programActivityName": "BES",
              "programActivityReportingKey": "PARK1", "amountCents": 500}]
        combined = combine_file_b_file_c(b, c, "089-0222", status)
        self.assertNotIn(
            "FY2024P03",
            {e["submissionPeriod"] for e in combined if e["source"] == "file_b_residual"})


class DollarTransientClassificationTests(unittest.TestCase):
    """Rule 4 of the snapshot-acceptance contract (Phase 3.2d remediation
    W14, 2026-09-21): a full-row-count File B period whose cumulative net
    obligations spikes or dips by more than 50% and then reverts is a
    transient inconsistent snapshot, invisible to the row-count rule. Real
    dod/navy-rdte cents (P10/P11/P12 FY2024 and P05/P06/P07 FY2023)."""

    def test_transient_spike_is_reclassified_not_reported(self):
        # dod/navy-rdte FY2024: P10 $25.41B, P11 $54.61B (spike), P12
        # $29.56B (reverts close to P10 and is the GTAS-reconciled total).
        row_status = {"FY2024P10": "reported", "FY2024P11": "reported",
                     "FY2024P12": "reported"}
        cumulative_cents = {"FY2024P10": 2_540_914_848_134,
                            "FY2024P11": 5_460_831_665_422,
                            "FY2024P12": 2_956_285_398_710}
        status = apply_dollar_transient_rule(row_status, cumulative_cents)
        self.assertEqual("notReported", status["FY2024P11"])
        self.assertEqual("reported", status["FY2024P10"])
        self.assertEqual("reported", status["FY2024P12"])

    def test_transient_dip_is_reclassified_not_reported(self):
        # A dip (rather than a spike) that reverts is caught the same way.
        row_status = {"FY2024P05": "reported", "FY2024P06": "reported",
                     "FY2024P07": "reported"}
        cumulative_cents = {"FY2024P05": 10_000_000_000,
                            "FY2024P06": 2_000_000_000,   # dip: -80%
                            "FY2024P07": 10_500_000_000}  # reverts near P05
        status = apply_dollar_transient_rule(row_status, cumulative_cents)
        self.assertEqual("notReported", status["FY2024P06"])

    def test_sustained_drop_stays_reported(self):
        # dhs/cisa-rd FY2023 shape: a real, sustained drop with no later
        # recovery must stay reported so the existing >50% drop check (and
        # its required baseline periodNotes) still governs it.
        row_status = {"FY2023P03": "reported", "FY2023P04": "reported",
                     "FY2023P05": "reported"}
        cumulative_cents = {"FY2023P03": 1_290_038_168,
                            "FY2023P04": 100_000_000,
                            "FY2023P05": 100_000_000}
        status = apply_dollar_transient_rule(row_status, cumulative_cents)
        self.assertEqual("reported", status["FY2023P04"])

    def test_below_floor_previous_cumulative_is_ignored(self):
        # A deviation that would otherwise qualify is skipped when the
        # preceding reported cumulative is below the $1M floor -- otherwise
        # a small account's cumulative can swing past 50% on noise.
        row_status = {"FY2022P02": "reported", "FY2022P03": "reported",
                     "FY2022P04": "reported"}
        cumulative_cents = {"FY2022P02": 24_258,
                            "FY2022P03": 5_000_000,  # a huge relative swing
                            "FY2022P04": 24_500}
        status = apply_dollar_transient_rule(row_status, cumulative_cents)
        self.assertEqual("reported", status["FY2022P03"])

    def test_final_period_is_exempt_even_if_pattern_qualifies(self):
        # The pattern must never reclassify the fiscal year's own final
        # period, even when the shape otherwise looks transient.
        row_status = {"FY2024P10": "reported", "FY2024P11": "reported",
                     "FY2024P12": "reported"}
        cumulative_cents = {"FY2024P10": 1_000_000_000,
                            "FY2024P11": 1_050_000_000,
                            "FY2024P12": 3_000_000_000}  # spikes at the end
        status = apply_dollar_transient_rule(row_status, cumulative_cents)
        self.assertEqual("reported", status["FY2024P12"])

    def test_classify_file_b_periods_applies_the_dollar_rule_when_given_cumulative(self):
        # classify_file_b_periods(row_counts) alone (no cumulative_cents)
        # reproduces the historical row-rule-only behavior; passing
        # cumulative_cents additionally applies rule 4.
        row_counts = {"FY2024P10": 221, "FY2024P11": 224, "FY2024P12": 227}
        cumulative_cents = {"FY2024P10": 2_540_914_848_134,
                            "FY2024P11": 5_460_831_665_422,
                            "FY2024P12": 2_956_285_398_710}
        row_only = classify_file_b_periods(row_counts)
        self.assertEqual({"FY2024P10": "reported", "FY2024P11": "reported",
                          "FY2024P12": "reported"}, row_only)
        with_dollar_rule = classify_file_b_periods(row_counts, cumulative_cents)
        self.assertEqual("notReported", with_dollar_rule["FY2024P11"])


# Navy-FY2024-like cumulative File B snapshot, in dollars as the source CSV
# would report it: full row counts every period, P10/P11/P12 the same real
# dod/navy-rdte cents as DollarTransientClassificationTests above (P11 a
# transient spike that P12 reverts from), P02-P09 a plain ramp so the rule
# has real preceding/following reported periods to compare against.
PULL_PATH_CUMULATIVE_DOLLARS = {
    2: "1000000000.00", 3: "3000000000.00", 4: "6000000000.00",
    5: "9000000000.00", 6: "12000000000.00", 7: "15000000000.00",
    8: "18000000000.00", 9: "21000000000.00",
    10: "25409148481.34", 11: "54608316654.22", 12: "29562853987.10",
}
PULL_PATH_ROW_COUNT = 200  # identical every period: the row rule alone
                           # never flags anything here.


def _pull_path_fake_download(cumulative_dollars, row_count):
    """Stand-in for scripts.pull_obligation_account._download.

    Returns the same (members, download-audit) shape ``_finish`` builds
    from a real accepted download, so ``file_b_row_counts_from_provenance``
    (used by ``account_period_status`` on the committed provenance) reads
    back exactly the row counts the pull saw.
    """
    def fake(repo, account, account_id, fy, period, kind, columns,
             raw_archive_dir=None, recovery=None, resume_handoffs=None,
             run_identity=None):
        if kind == "object_class_program_activity":
            members = {"ob_pa.csv": [{
                "federal_account_symbol": account["federalAccount"],
                "program_activity_code": "0001",
                "program_activity_name": "RDTE",
                "obligations_incurred": cumulative_dollars[period],
            }]}
            download = {
                "statusRowCount": row_count,
                "acceptedRequestScope": {
                    "download_types": ["object_class_program_activity"],
                    "filters": {"fy": fy, "period": period},
                },
            }
            return members, download
        assert kind == "award_financial", kind
        members = {"assistance.csv": [], "contract.csv": [], "unlinked.csv": []}
        download = {
            "statusRowCount": 0,
            "acceptedRequestScope": {
                "download_types": ["award_financial"],
                "filters": {"fy": fy, "period": period},
            },
        }
        return members, download
    return fake


class PullPathDollarTransientClassificationTests(unittest.TestCase):
    """W19 (Phase 3.2d remediation follow-up to W14/PR #80):
    scripts/pull_obligation_account.py's pull() must classify File B
    periods for pin advancement and logging with the dollar-transient rule
    applied (``published_classification``), using the identical
    cumulative-cents formula (``fy_cumulative_cents``) the rebuild/
    validator path (``account_period_status``) uses -- while event
    construction stays on the row-rule-only classification so stored bytes
    do not change. See the W19 comment in pull_obligation_account.py's
    ``pull()`` for the full rationale."""

    def _account(self, repo):
        (repo / "reference").mkdir(parents=True, exist_ok=True)
        baseline_path = repo / "reference" / "pull_path_test_baseline.json"
        baseline_path.write_text(json.dumps({
            "schemaVersion": 2, "federalAccount": "017-1319", "fiscalYears": {},
        }))
        return {
            "path": "dod/navy-rdte-w19-test",
            "name": "Test Navy RDTE",
            "federalAccount": "017-1319",
            "baseline": "reference/pull_path_test_baseline.json",
            "availability": {"firstFiscalYear": 2024, "firstFiscalYearPeriod": 2,
                             "regularFirstPeriod": 2},
            "programActivities": [{"slug": "rdte", "code": "0001", "name": "RDTE"}],
        }

    def _pull(self, repo):
        account = self._account(repo)
        fake_download = _pull_path_fake_download(
            PULL_PATH_CUMULATIVE_DOLLARS, PULL_PATH_ROW_COUNT
        )
        with patch("scripts.pull_obligation_account.resolve_account",
                   return_value=("12345", {})), \
             patch("scripts.pull_obligation_account._download",
                   side_effect=fake_download):
            pull(account, [2024], repo=repo, rollup=False)
        return account

    def test_pin_advancement_matches_rebuild_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            account = self._pull(repo)
            store = repo / "data" / "obligations" / account["path"] / "events"
            events = load_store(store)
            provenance = json.loads(
                (store / "FY2024.provenance.json").read_text())
            pin_period = provenance["baselinePin"]["asOfPeriod"]
            rebuild_status = account_period_status(
                store, events, partial_fys=set())
            self.assertEqual("notReported", rebuild_status["FY2024P11"])
            self.assertEqual("reported", rebuild_status["FY2024P10"])
            self.assertEqual("reported", rebuild_status["FY2024P12"])
            reported_periods = [
                period_info(label)[1]
                for label, status in rebuild_status.items()
                if status == "reported"
            ]
            # (a) the classification used for pin advancement equals
            # account_period_status computed on the resulting events.
            self.assertEqual(max(reported_periods), pin_period)
            # (c) effective_last_period is unchanged: the dollar rule never
            # reclassifies a fiscal year's own final period, so P12 (the
            # highest-numbered reported period either way) still pins it.
            self.assertEqual(12, pin_period)

    def test_stored_events_are_row_rule_only_no_storage_change(self):
        # (b) stored events equal those the row-rule-only classification
        # would produce -- P11 must NOT be folded away by the dollar rule
        # at storage time, or account_period_status's cumulative-from-
        # events derivation would never see the spike to reclassify.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            account = self._pull(repo)
            store = repo / "data" / "obligations" / account["path"] / "events"
            stored_events = [e for e in load_store(store)
                             if e["fiscalYear"] == 2024]

            aliases = alias_map(account)
            file_b_row_counts = {
                f"FY2024P{p:02d}": PULL_PATH_ROW_COUNT for p in range(2, 13)
            }
            row_classification = classify_file_b_periods(file_b_row_counts)
            self.assertTrue(
                all(status == "reported"
                    for status in row_classification.values()),
                row_classification,
            )
            snapshots = {}
            for period in range(2, 13):
                label = f"FY2024P{period:02d}"
                rows = [{
                    "federal_account_symbol": account["federalAccount"],
                    "program_activity_code": "0001",
                    "program_activity_name": "RDTE",
                    "obligations_incurred": PULL_PATH_CUMULATIVE_DOLLARS[period],
                }]
                snapshots[label] = parse_file_b_snapshot(
                    rows, account["federalAccount"], aliases)
            expected_file_b = file_b_period_events(
                snapshots, account["federalAccount"], row_classification)
            expected_events = [
                normalize_event(e) for e in combine_file_b_file_c(
                    expected_file_b, [], account["federalAccount"],
                    row_classification,
                )
            ]
            self.assertEqual(
                sorted(e["id"] for e in expected_events),
                sorted(e["id"] for e in stored_events),
            )
            expected_by_id = {e["id"]: e for e in expected_events}
            for stored in stored_events:
                self.assertEqual(
                    expected_by_id[stored["id"]]["amountCents"],
                    stored["amountCents"],
                    stored["id"],
                )
            # P11's own delta is really stored, not skipped/folded away.
            p11_amount = sum(e["amountCents"] for e in stored_events
                             if e["submissionPeriod"] == "FY2024P11")
            self.assertNotEqual(0, p11_amount)

    def test_dollar_transient_reclassifications_are_logged(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            with patch("builtins.print") as fake_print:
                self._pull(repo)
            lines = [call.args[0] for call in fake_print.call_args_list
                    if call.args]
            transient_lines = [line for line in lines
                               if line.startswith("DOLLAR-TRANSIENT:")]
            self.assertEqual(
                ["DOLLAR-TRANSIENT: dod/navy-rdte-w19-test FY2024 P11 "
                 "reported -> notReported"],
                transient_lines,
            )

    def test_events_derived_cumulative_reconstructs_the_navy_cents(self):
        # The stored events -- built from the row-rule-only classification,
        # per (b) above -- must still telescope back to the real Navy
        # cumulative cents through fy_cumulative_cents, the same formula
        # both the pull path and account_period_status call. This is what
        # lets the rebuild path rediscover the P11 spike from committed
        # events alone, with no network pull.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            account = self._pull(repo)
            store = repo / "data" / "obligations" / account["path"] / "events"
            events = load_store(store)
            fy_events = [e for e in events if e["fiscalYear"] == 2024]
            labels = [f"FY2024P{p:02d}" for p in range(2, 13)]
            cumulative = fy_cumulative_cents(fy_events, labels)
            self.assertEqual(2_540_914_848_134, cumulative["FY2024P10"])
            self.assertEqual(5_460_831_665_422, cumulative["FY2024P11"])
            self.assertEqual(2_956_285_398_710, cumulative["FY2024P12"])


if __name__ == "__main__":
    unittest.main()
