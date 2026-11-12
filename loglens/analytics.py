import math
from typing import Any, Dict, List

from loglens.storage import LogStore


def compute_p95(sorted_values: List[int]) -> int:
    if not sorted_values:
        return 0
    idx = max(0, math.ceil(0.95 * len(sorted_values)) - 1)
    return sorted_values[idx]


def generate_report(store: LogStore, burst_threshold: int = 3) -> Dict[str, Any]:
    cur = store.conn.cursor()
    summary = cur.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status >= 400 AND status < 500 THEN 1 ELSE 0 END), 0) AS client_errors,
            COALESCE(SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END), 0) AS server_errors,
            COALESCE(AVG(latency_ms), 0.0) AS avg_latency_ms
        FROM logs
        """
    ).fetchone()

    total = summary["total"]
    latencies = [r[0] for r in cur.execute("SELECT latency_ms FROM logs ORDER BY latency_ms ASC").fetchall()]

    top_slow = [
        {"path": r["path"], "avg_latency_ms": round(r["avg_ms"], 2), "hits": r["hits"]}
        for r in cur.execute(
            """
            SELECT path, AVG(latency_ms) AS avg_ms, COUNT(*) AS hits
            FROM logs
            GROUP BY path
            ORDER BY avg_ms DESC, hits DESC
            LIMIT 5
            """
        ).fetchall()
    ]

    error_bursts = [
        {"ip": r["ip"], "error_count": r["err_cnt"]}
        for r in cur.execute(
            """
            SELECT ip, COUNT(*) AS err_cnt
            FROM logs
            WHERE status >= 400
            GROUP BY ip
            HAVING COUNT(*) >= ?
            ORDER BY err_cnt DESC
            """,
            (burst_threshold,),
        ).fetchall()
    ]

    error_total = summary["client_errors"] + summary["server_errors"]
    return {
        "total_requests": total,
        "client_errors_4xx": summary["client_errors"],
        "server_errors_5xx": summary["server_errors"],
        "error_rate_pct": round((error_total / total) * 100, 2) if total else 0.0,
        "avg_latency_ms": round(summary["avg_latency_ms"], 2),
        "p95_latency_ms": compute_p95(latencies),
        "top_slow_endpoints": top_slow,
        "suspicious_error_ips": error_bursts,
    }
