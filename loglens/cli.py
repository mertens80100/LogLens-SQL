import argparse
import json
from pathlib import Path
from typing import List, Optional

from loglens.analytics import generate_report
from loglens.storage import LogStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="loglens", description="LogLens-SQL: Server log analytics CLI")
    parser.add_argument("--db", default="loglens.db", help="Path to SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Ingest a log file into SQLite")
    p_ingest.add_argument("logfile", help="Path to log file")

    p_query = sub.add_parser("query", help="Filter ingested logs")
    p_query.add_argument("--min-status", type=int)
    p_query.add_argument("--max-status", type=int)
    p_query.add_argument("--path-prefix")
    p_query.add_argument("--ip")
    p_query.add_argument("--min-latency-ms", type=int)
    p_query.add_argument("--limit", type=int, default=50)

    p_report = sub.add_parser("report", help="Generate JSON analytics & anomaly report")
    p_report.add_argument("--burst-threshold", type=int, default=3)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    store = LogStore(args.db)
    try:
        if args.command == "ingest":
            lines = Path(args.logfile).read_text(encoding="utf-8").splitlines()
            inserted, malformed = store.ingest_lines(lines)
            print(json.dumps({"inserted": inserted, "malformed": malformed}))
            return 0

        if args.command == "query":
            entries = store.query(
                min_status=args.min_status,
                max_status=args.max_status,
                path_prefix=args.path_prefix,
                ip=args.ip,
                min_latency_ms=args.min_latency_ms,
                limit=args.limit,
            )
            print(json.dumps([e.__dict__ for e in entries], indent=2))
            return 0

        if args.command == "report":
            report = generate_report(store, burst_threshold=args.burst_threshold)
            print(json.dumps(report, indent=2))
            return 0
    finally:
        store.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
