import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from loglens.analytics import compute_p95, generate_report
from loglens.cli import main as cli_main
from loglens.parser import parse_log_line
from loglens.storage import LogStore


class TestLogLens(unittest.TestCase):
    def test_parse_valid_and_invalid_lines(self):
        valid = parse_log_line("2026-11-10T10:00:01Z 10.0.0.1 GET /api/health 200 15ms")
        self.assertIsNotNone(valid)
        self.assertEqual(valid.status, 200)
        self.assertEqual(valid.latency_ms, 15)

        self.assertIsNone(parse_log_line("# comment line"))
        self.assertIsNone(parse_log_line("corrupted line without fields"))
        self.assertIsNone(parse_log_line("2026-11-10T10:00:01Z 10.0.0.1 GET /api/x 999 10ms"))

    def test_ingest_query_and_analytics(self):
        store = LogStore(":memory:")
        lines = [
            "2026-11-10T10:00:01Z 10.0.0.1 GET /api/tasks 200 20ms",
            "2026-11-10T10:00:02Z 192.168.1.9 POST /api/login 401 10ms",
            "2026-11-10T10:00:03Z 192.168.1.9 POST /api/login 401 12ms",
            "2026-11-10T10:00:04Z 192.168.1.9 POST /api/login 403 14ms",
            "2026-11-10T10:00:05Z 10.0.0.2 GET /api/export 500 500ms",
            "bad log line",
        ]
        inserted, malformed = store.ingest_lines(lines)
        self.assertEqual(inserted, 5)
        self.assertEqual(malformed, 1)

        errors = store.query(min_status=500)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].path, "/api/export")

        report = generate_report(store, burst_threshold=3)
        self.assertEqual(report["total_requests"], 5)
        self.assertEqual(report["server_errors_5xx"], 1)
        self.assertEqual(report["client_errors_4xx"], 3)
        self.assertEqual(report["p95_latency_ms"], 500)
        self.assertEqual(report["suspicious_error_ips"][0]["ip"], "192.168.1.9")
        store.close()

    def test_p95_helper(self):
        self.assertEqual(compute_p95([]), 0)
        self.assertEqual(compute_p95([10, 20, 30, 40, 100]), 100)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "test.db")
            log_path = str(Path(tmp) / "app.log")
            Path(log_path).write_text(
                "2026-11-10T10:00:01Z 10.0.0.1 GET /api/tasks 200 25ms\n"
                "2026-11-10T10:00:02Z 10.0.0.2 GET /api/tasks 500 250ms\n",
                encoding="utf-8",
            )

            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(["--db", db_path, "ingest", log_path])
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(buf.getvalue())["inserted"], 2)

            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                rc2 = cli_main(["--db", db_path, "query", "--min-status", "500"])
            self.assertEqual(rc2, 0)
            rows = json.loads(buf2.getvalue())
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], 500)


if __name__ == "__main__":
    unittest.main()
