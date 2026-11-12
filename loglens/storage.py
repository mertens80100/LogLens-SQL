import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from loglens.parser import LogEntry, parse_log_line

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    ip TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_status ON logs(status);
CREATE INDEX IF NOT EXISTS idx_logs_path ON logs(path);
CREATE INDEX IF NOT EXISTS idx_logs_ip ON logs(ip);
"""


class LogStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA_SQL)

    def close(self) -> None:
        self.conn.close()

    def ingest_lines(self, lines: Iterable[str]) -> Tuple[int, int]:
        valid_rows = []
        malformed = 0
        for raw in lines:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            entry = parse_log_line(raw)
            if entry is None:
                malformed += 1
            else:
                valid_rows.append((
                    entry.timestamp,
                    entry.ip,
                    entry.method,
                    entry.path,
                    entry.status,
                    entry.latency_ms,
                ))
        with self.conn:
            self.conn.executemany(
                "INSERT INTO logs (timestamp, ip, method, path, status, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
                valid_rows,
            )
        return len(valid_rows), malformed

    def query(
        self,
        min_status: Optional[int] = None,
        max_status: Optional[int] = None,
        path_prefix: Optional[str] = None,
        ip: Optional[str] = None,
        min_latency_ms: Optional[int] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        clauses = []
        params: list = []
        if min_status is not None:
            clauses.append("status >= ?")
            params.append(min_status)
        if max_status is not None:
            clauses.append("status <= ?")
            params.append(max_status)
        if path_prefix is not None:
            clauses.append("path LIKE ?")
            params.append(f"{path_prefix}%")
        if ip is not None:
            clauses.append("ip = ?")
            params.append(ip)
        if min_latency_ms is not None:
            clauses.append("latency_ms >= ?")
            params.append(min_latency_ms)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT timestamp, ip, method, path, status, latency_ms
            FROM logs
            {where_sql}
            ORDER BY id ASC
            LIMIT ?
        """
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [
            LogEntry(
                timestamp=r["timestamp"],
                ip=r["ip"],
                method=r["method"],
                path=r["path"],
                status=r["status"],
                latency_ms=r["latency_ms"],
            )
            for r in rows
        ]
