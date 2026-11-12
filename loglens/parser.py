import re
from dataclasses import dataclass
from typing import Optional

LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\S+)\s+"
    r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+"
    r"(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+"
    r"(?P<path>/\S*)\s+"
    r"(?P<status>\d{3})\s+"
    r"(?P<latency_ms>\d+)ms$"
)


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    ip: str
    method: str
    path: str
    status: int
    latency_ms: int


def parse_log_line(line: str) -> Optional[LogEntry]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    match = LOG_PATTERN.match(stripped)
    if not match:
        return None
    status = int(match.group("status"))
    if status < 100 or status > 599:
        return None
    return LogEntry(
        timestamp=match.group("timestamp"),
        ip=match.group("ip"),
        method=match.group("method"),
        path=match.group("path"),
        status=status,
        latency_ms=int(match.group("latency_ms")),
    )
