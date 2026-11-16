from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.providers.aimidas_snapshot import (
    BRAZIL_SERIE_B_2026,
    SnapshotError,
    audit_csv,
    collect_snapshot,
    git_blob_sha1,
    sha256,
)


def sample_csv() -> bytes:
    return (
        "Team,Goals,Goals Conceded,Match,Date\n"
        "Home FC,2,1,Home FC 2-1 Away FC,2026-01-10\n"
        "Away FC,1,2,Home FC 2-1 Away FC,2026-01-10\n"
    ).encode("utf-8")


def sample_spec(raw: bytes):
    return replace(
        BRAZIL_SERIE_B_2026,
        expected_git_blob_sha1=git_blob_sha1(raw),
        expected_sha256=sha256(raw),
        expected_bytes=len(raw),
        expected_rows=2,
        expected_matches=1,
        expected_teams=2,
        date_min="2026-01-10",
        date_max="2026-01-10",
    )


def test_snapshot_audit_verifies_match_pair_and_score_orientation() -> None:
    raw = sample_csv()
    audit = audit_csv(raw, sample_spec(raw))

    assert audit["row_count"] == 2
    assert audit["match_count"] == 1
    assert audit["team_count"] == 2
    assert audit["point_in_time_certifiable"] is False


def test_snapshot_audit_rejects_team_score_mismatch() -> None:
    raw = sample_csv().replace(b"Home FC,2,1", b"Home FC,1,1")
    with pytest.raises(SnapshotError, match="TEAM_SCORE_ORIENTATION_MISMATCH"):
        audit_csv(raw, sample_spec(raw))


def test_snapshot_audit_rejects_duplicate_team_rows() -> None:
    raw = (
        "Team,Goals,Goals Conceded,Match,Date\n"
        "Home FC,2,1,Home FC 2-1 Away FC,2026-01-10\n"
        "Home FC,2,1,Home FC 2-1 Away FC,2026-01-10\n"
    ).encode("utf-8")
    with pytest.raises(SnapshotError, match="MATCH_TEAM_ROW_CARDINALITY_INVALID"):
        audit_csv(raw, sample_spec(raw))


def test_collector_writes_private_snapshot_and_restricted_manifest(tmp_path: Path) -> None:
    raw = sample_csv()
    manifest = collect_snapshot(
        tmp_path,
        fetcher=lambda spec: raw,
        retrieved_at=datetime(2026, 11, 16, 12, 0, tzinfo=UTC),
        spec=sample_spec(raw),
    )

    stored = tmp_path / "snapshots" / BRAZIL_SERIE_B_2026.path
    assert stored.read_bytes() == raw
    assert manifest["rights_scope"] == "NON_COMMERCIAL_ONLY"
    assert manifest["raw_redistribution_allowed"] is False
    assert manifest["raw_data_committed_to_git"] is False
    assert manifest["point_in_time_certifiable"] is False
    assert manifest["model_admitted"] is False
    assert (tmp_path / "manifest.json").exists()


def test_collector_rejects_naive_retrieval_timestamp(tmp_path: Path) -> None:
    with pytest.raises(SnapshotError, match="RETRIEVAL_TIMESTAMP_MUST_BE_TIMEZONE_AWARE"):
        collect_snapshot(
            tmp_path,
            fetcher=lambda spec: sample_csv(),
            retrieved_at=datetime(2026, 11, 16, 12, 0),
            spec=sample_spec(sample_csv()),
        )
