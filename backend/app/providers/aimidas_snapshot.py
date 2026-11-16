"""Pinned, non-commercial AI Midas CSV snapshot capture.

Only a single approved Brazil Serie B file is captured. Raw bytes stay outside
Git; this module performs no database writes, model operations, or predictions.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from collections.abc import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class SnapshotSpec:
    repository: str
    commit: str
    approval_id: str
    path: str
    expected_git_blob_sha1: str
    expected_sha256: str
    expected_bytes: int
    expected_rows: int
    expected_matches: int
    expected_teams: int
    date_min: str
    date_max: str


BRAZIL_SERIE_B_2026 = SnapshotSpec(
    repository="aimidas1/aimidas1",
    commit="29baca362a34ce5dcd3924b07ec9c7d5139d83fc",
    approval_id="approval-aimidas-football-data-noncommercial-2026-11-15",
    path="advanced stats/Brazil Serie B 2026.csv",
    expected_git_blob_sha1="b6bdb94c053d2149e6232fb100e1f158e46e4533",
    expected_sha256="55b0c00629abd2d4ff3c31659ada950b67ffc2752609284b32c15c99f71152ab",
    expected_bytes=192284,
    expected_rows=738,
    expected_matches=369,
    expected_teams=20,
    date_min="2026-03-21",
    date_max="2026-11-08",
)

MATCH_PATTERN = re.compile(
    r"^(?P<home>.+) (?P<home_goals>\d+)-(?P<away_goals>\d+) (?P<away>.+)$"
)
USER_AGENT = "VELTRIX-AI-ANALYST-AIMidas-Snapshot/1.0"


class SnapshotError(ValueError):
    """Raised when the pinned snapshot fails integrity or schema checks."""


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def _non_negative_integer(value: str, field_name: str, line_number: int) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise SnapshotError(f"INVALID_INTEGER:{field_name}:line={line_number}") from None
    if not number.is_integer() or number < 0:
        raise SnapshotError(f"INVALID_INTEGER:{field_name}:line={line_number}")
    return int(number)


def audit_csv(raw: bytes, spec: SnapshotSpec = BRAZIL_SERIE_B_2026) -> dict[str, object]:
    if len(raw) != spec.expected_bytes:
        raise SnapshotError("SOURCE_BYTE_COUNT_MISMATCH")
    if sha256(raw) != spec.expected_sha256:
        raise SnapshotError("SOURCE_SHA256_MISMATCH")
    if git_blob_sha1(raw) != spec.expected_git_blob_sha1:
        raise SnapshotError("SOURCE_GIT_BLOB_SHA1_MISMATCH")

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise SnapshotError("SOURCE_CSV_NOT_UTF8") from None

    reader = csv.DictReader(io.StringIO(decoded, newline=""))
    required = {"Team", "Match", "Date", "Goals", "Goals Conceded"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise SnapshotError("SOURCE_REQUIRED_COLUMNS_MISSING")

    grouped: dict[tuple[str, str], list[tuple[str, int, int, str, int, int]]] = {}
    teams: set[str] = set()
    dates: list[date] = []
    row_count = 0

    for line_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue
        row_count += 1
        team = (row.get("Team") or "").strip()
        match_label = (row.get("Match") or "").strip()
        date_raw = (row.get("Date") or "").strip()
        if not team or not match_label or not date_raw:
            raise SnapshotError(f"REQUIRED_VALUE_MISSING:line={line_number}")
        try:
            match_date = date.fromisoformat(date_raw)
        except ValueError:
            raise SnapshotError(f"INVALID_MATCH_DATE:line={line_number}") from None
        match = MATCH_PATTERN.fullmatch(match_label)
        if match is None:
            raise SnapshotError(f"INVALID_MATCH_LABEL:line={line_number}")

        home = match.group("home").strip()
        away = match.group("away").strip()
        home_goals = int(match.group("home_goals"))
        away_goals = int(match.group("away_goals"))
        goals = _non_negative_integer(row.get("Goals", ""), "Goals", line_number)
        conceded = _non_negative_integer(
            row.get("Goals Conceded", ""), "Goals Conceded", line_number
        )
        if team == home:
            expected = (home_goals, away_goals)
        elif team == away:
            expected = (away_goals, home_goals)
        else:
            raise SnapshotError(f"TEAM_NOT_IN_MATCH_LABEL:line={line_number}")
        if (goals, conceded) != expected:
            raise SnapshotError(f"TEAM_SCORE_ORIENTATION_MISMATCH:line={line_number}")

        key = (match_date.isoformat(), match_label)
        grouped.setdefault(key, []).append(
            (team, goals, conceded, home, home_goals, away_goals)
        )
        teams.add(team)
        dates.append(match_date)

    if row_count != spec.expected_rows:
        raise SnapshotError("SOURCE_ROW_COUNT_MISMATCH")
    if len(grouped) != spec.expected_matches:
        raise SnapshotError("SOURCE_MATCH_COUNT_MISMATCH")
    for key, rows in grouped.items():
        if len(rows) != 2 or len({row[0] for row in rows}) != 2:
            raise SnapshotError(f"MATCH_TEAM_ROW_CARDINALITY_INVALID:{key[0]}")
        if {row[0] for row in rows} != {
            rows[0][3],
            MATCH_PATTERN.fullmatch(key[1]).group("away").strip(),
        }:
            raise SnapshotError(f"MATCH_TEAM_IDENTITY_MISMATCH:{key[0]}")

    if len(teams) != spec.expected_teams:
        raise SnapshotError("SOURCE_TEAM_COUNT_MISMATCH")

    date_min = min(dates).isoformat()
    date_max = max(dates).isoformat()
    if date_min != spec.date_min or date_max != spec.date_max:
        raise SnapshotError("SOURCE_DATE_RANGE_MISMATCH")

    return {
        "row_count": row_count,
        "match_count": len(grouped),
        "team_count": len(teams),
        "date_min": date_min,
        "date_max": date_max,
        "sha256": spec.expected_sha256,
        "git_blob_sha1": spec.expected_git_blob_sha1,
        "point_in_time_certifiable": False,
    }


def fetch_raw(spec: SnapshotSpec = BRAZIL_SERIE_B_2026) -> bytes:
    encoded_path = quote(spec.path, safe="/")
    url = (
        f"https://raw.githubusercontent.com/{spec.repository}/"
        f"{spec.commit}/{encoded_path}"
    )
    request = Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv"},
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise SnapshotError(f"SOURCE_HTTP_STATUS:{response.status}")
        raw = response.read(spec.expected_bytes + 1)
    if len(raw) > spec.expected_bytes:
        raise SnapshotError("SOURCE_EXCEEDS_PINNED_BYTE_COUNT")
    return raw


def _validate_private_output_path(output_dir: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    target = output_dir.resolve()
    try:
        relative = target.relative_to(repository_root)
    except ValueError:
        return
    if not relative.parts or relative.parts[0] != ".local-data":
        raise SnapshotError("RAW_SNAPSHOT_MUST_BE_STORED_OUTSIDE_PUBLIC_REPOSITORY")


def collect_snapshot(
    output_dir: Path,
    *,
    fetcher: Callable[[SnapshotSpec], bytes] = fetch_raw,
    retrieved_at: datetime | None = None,
    spec: SnapshotSpec = BRAZIL_SERIE_B_2026,
) -> dict[str, object]:
    _validate_private_output_path(output_dir)
    retrieved_at = retrieved_at or datetime.now(UTC)
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise SnapshotError("RETRIEVAL_TIMESTAMP_MUST_BE_TIMEZONE_AWARE")

    raw = fetcher(spec)
    audit = audit_csv(raw, spec)
    snapshot_path = output_dir / "snapshots" / spec.path
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_bytes(raw)

    manifest: dict[str, object] = {
        "schema_version": "veltrix-ai-analyst-aimidas-snapshot-v1",
        "source_repository": spec.repository,
        "source_commit": spec.commit,
        "source_path": spec.path,
        "approval_id": spec.approval_id,
        "retrieved_at_utc": retrieved_at.astimezone(UTC).isoformat(),
        "attribution": "AI Midas Football Data",
        "rights_scope": "NON_COMMERCIAL_ONLY",
        "raw_redistribution_allowed": False,
        "raw_data_committed_to_git": False,
        "raw_file_sha256": audit["sha256"],
        "raw_file_git_blob_sha1": audit["git_blob_sha1"],
        "raw_file_bytes": len(raw),
        "row_count": audit["row_count"],
        "match_count": audit["match_count"],
        "team_count": audit["team_count"],
        "date_min": audit["date_min"],
        "date_max": audit["date_max"],
        "source_publication_timestamp_available": False,
        "point_in_time_certifiable": False,
        "pre_match_feature_eligible": False,
        "model_admitted": False,
        "database_written": False,
        "predictions_changed": False,
        "snapshot_relative_path": snapshot_path.relative_to(output_dir).as_posix(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
