from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "materialize_approved_scopes.py"
SPEC = importlib.util.spec_from_file_location("materialize_approved_scopes", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        assert "source_approvals" in sql
        assert "statement_timestamp()" in sql
        self.rows = self.connection.approvals

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.approvals = [
            {
                "approval_id": "approval-a",
                "provider": "ProviderA",
                "source_id": "provider-a",
                "scope_values": ["league-1", "league-2", "league-1"],
                "effective_status": "APPROVED",
            }
        ]

    def cursor(self, row_factory=None):
        return FakeCursor(self)


def test_approved_scope_enumerator_expands_competition_ids_without_duplicates():
    scopes = MODULE._approved_scopes(FakeConnection())
    assert [
        (scope.provider, scope.source_id, scope.competition_id, scope.rights_approval_id)
        for scope in scopes
    ] == [
        ("ProviderA", "provider-a", "league-1", "approval-a"),
        ("ProviderA", "provider-a", "league-2", "approval-a"),
    ]
    assert all(scope.import_run_id is None for scope in scopes)


def test_exact_scope_selector_rejects_partial_selector():
    scopes = MODULE._approved_scopes(FakeConnection())
    try:
        MODULE._select_scope(scopes, "ProviderA", None, "league-1")
    except ValueError as exc:
        assert str(exc) == "EXACT_SCOPE_REQUIRES_PROVIDER_SOURCE_AND_COMPETITION"
    else:
        raise AssertionError("partial scope selector must fail closed")


def test_exact_scope_selector_returns_only_requested_scope():
    scopes = MODULE._approved_scopes(FakeConnection())
    selected = MODULE._select_scope(
        scopes, "ProviderA", "provider-a", "league-2"
    )
    assert [scope.competition_id for scope in selected] == ["league-2"]


def test_dry_run_reports_every_approved_scope_without_writes(monkeypatch):
    class Plan:
        ready = True

        @staticmethod
        def as_dict():
            return {"ready": True, "fixture_count": 0}

    calls = []
    monkeypatch.setattr(
        MODULE,
        "build_canonical_materialization_plan",
        lambda connection, scope: (calls.append(scope.competition_id) or Plan()),
    )
    report = MODULE.run(FakeConnection())
    assert report["mode"] == "DRY_RUN"
    assert report["provider_requests_made"] == 0
    assert report["scope_count"] == 2
    assert report["ready_count"] == 2
    assert report["blocked_count"] == 0
    assert calls == ["league-1", "league-2"]


def test_identity_alias_rules_are_explicit_and_scope_local():
    from datetime import UTC, datetime, timedelta

    from app.canonicalization import _identity_collision_fixture_ids

    kickoff = datetime(2026, 3, 22, 21, tzinfo=UTC)
    fixtures = [
        {
            "provider_fixture_id": "fixture-a",
            "home_team_provider_id": "opponent",
            "away_team_provider_id": "team-a",
            "kickoff_at": kickoff,
        },
        {
            "provider_fixture_id": "fixture-b",
            "home_team_provider_id": "opponent",
            "away_team_provider_id": "team-b",
            "kickoff_at": kickoff + timedelta(seconds=60),
        },
    ]
    assert _identity_collision_fixture_ids(fixtures) == ()
    assert _identity_collision_fixture_ids(fixtures, (("team-a", "team-b"),)) == (
        "fixture-a",
        "fixture-b",
    )


def test_write_gate_requires_every_canonical_and_prediction_migration():
    applied = {
        "006_pre_match_feature_pit_gate.sql",
        "007_canonical_entity_layer.sql",
        "008_model_artifacts.sql",
        "008_canonical_identity_link_uniqueness.sql",
        "009_canonical_identity_review_cases.sql",
        "010_system_observed_pit.sql",
        "011_import_run_competition_scope.sql",
        "012_database_observed_timestamps.sql",
        "013_target_fixture_pre_match_gate.sql",
    }
    assert MODULE._missing_required_migrations(applied) == [
        "014_prediction_publication_storage.sql",
        "015_automated_identity_adjudication.sql",
    ]


def test_apply_requires_one_effective_approval_for_exact_scope():
    connection = FakeConnection()
    connection.approvals.append({
        **connection.approvals[0],
        "approval_id": "approval-b",
    })
    try:
        MODULE.run(
            connection,
            execute=True,
            provider="ProviderA",
            source_id="provider-a",
            competition_id="league-1",
        )
    except ValueError as exc:
        assert str(exc) == "EXACT_SCOPE_MUST_RESOLVE_TO_ONE_EFFECTIVE_APPROVAL"
    else:
        raise AssertionError("ambiguous active approvals must block writes")
