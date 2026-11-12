# LogLens-SQL

A fast, zero-dependency **Server Log Ingestion, SQLite Analytics & Anomaly Detection CLI** written in **Python 3.11** (`sqlite3`, `re`, `argparse`, `unittest`).

## Key Capabilities
- **Streaming Log Ingestion**: Parses structured access logs into an indexed SQLite schema while tracking malformed lines without crashing.
- **SQL-Backed Search**: Filters logs by HTTP status range (`--min-status`, `--max-status`), endpoint prefix (`--path-prefix`), client IP, and latency threshold (`--min-latency-ms`).
- **Latency & Error Analytics**: Computes total requests, 4xx/5xx error rates, average & p95 latency, top slowest endpoints, and suspicious IP error bursts.
- **Automated Test Suite & CI**: Full `unittest` coverage for log parsing, SQL queries, percentile math, burst detection, and CLI end-to-end flows via GitHub Actions.

## Quick Start

```bash
python3 -m loglens.cli --db loglens.db ingest sample_logs.log
python3 -m loglens.cli --db loglens.db query --min-status 500 --min-latency-ms 200
python3 -m loglens.cli --db loglens.db report --burst-threshold 3
python3 -m unittest discover -s tests -v
```
