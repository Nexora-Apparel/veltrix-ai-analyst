from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "canonical_scope_inventory.py"
SPEC = importlib.util.spec_from_file_location("canonical_scope_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class FakeCursor:
    def __init__(self, connection):
        self.connection=connection
        self.result=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def execute(self,sql,params=None):
        self.connection.queries.append((sql,params))
        if "FROM veltrix_ai_analyst.source_approvals approval" in sql:
            self.result=self.connection.approvals
        elif "SELECT version FROM public.schema_migrations" in sql:
            self.result=[{"version":v} for v in self.connection.migrations]
        elif "to_regclass" in sql:
            self.result=[self.connection.schema]
        elif "competition_rows" in sql:
            self.result=[self.connection.competition_counts]
        elif "linked_fixture_rows" in sql:
            self.result=[self.connection.canonical_counts]
        elif "fixture_rows" in sql:
            self.result=[self.connection.fixture_counts]
        elif "referenced_team_ids" in sql:
            self.result=[self.connection.team_counts]
        elif "unresolved_cases" in sql:
            self.result=[{"unresolved_cases":2}]
        elif "GROUP BY c.case_type" in sql:
            self.result=self.connection.review_case_breakdown
        elif "review_case.case_key" in sql:
            self.result=self.connection.unlinked_global_review_cases
        else:
            raise AssertionError("Unexpected query")
    def fetchall(self): return self.result
    def fetchone(self): return self.result[0]


class FakeConnection:
    def __init__(self):
        self.queries=[]
        self.approvals=[{
            "approval_id":"approval-x","provider":"P","source_id":"S",
            "scope_type":"competition_id","scope_values":["42"],
            "data_types":["fixtures_and_results"],"permitted_uses":["internal"],
            "recorded_status":"APPROVED","valid_from":datetime.now(UTC),"valid_until":None,
            "approval_in_validity_interval":True,
            "commercial_use_allowed":False,"evidence_uri":"e","evidence_sha256":"x",
            "effective_status":"APPROVED","effective_status_at":None,
        }]
        self.migrations=set(MODULE.REQUIRED_MIGRATIONS)
        self.schema={k:True for k in ("competitions","teams","fixtures","observations","sightings","fixture_links","team_identity_links","competition_identity_links","canonical_teams","canonical_competitions","canonical_fixtures","identity_review_cases","identity_review_events","canonical_identity_review_events","effective_team_links","effective_competition_links","effective_approvals","team_alias_case_audit","effective_team_aliases","team_provenance_audit","competition_provenance_audit","fixture_provenance_audit","duplicate_case_audit","effective_fixture_deduplication","effective_fixture_sources","review_cases")}
        self.competition_counts={"competition_rows":1,"observation_linked":1,"provenance_complete":1,"canonical_linked_competitions":1,"identity_review_required":1,"identity_conflicts":0}
        self.review_case_breakdown=[{"case_type":"FIXTURE_DUPLICATE_CANDIDATE","effective_case_status":"OPEN","case_count":1}]
        self.unlinked_global_review_cases=[{"case_key":"PIT_GAP","case_type":"PIT_TIMESTAMP_GAP","effective_case_status":"AUTOMATED_DEFERRED","effective_human_review_required":False,"recommended_action":"KEEP_OUT_OF_FEATURES"}]
        self.fixture_counts={"fixture_rows":3,"finished":2,"scheduled":1,"live":0,"unknown_status":0,"fixture_observation_linked":3,"fixture_provenance_complete":2}
        self.team_counts={"referenced_team_ids":2,"catalogued_teams":2,"observation_linked_teams":2,"provenance_complete_teams":2,"canonical_linked_teams":2,"identity_review_required":2,"identity_conflicts":0}
        self.canonical_counts={"linked_fixture_rows":1,"source_links":1,"source_link_review_required":1,"source_link_conflicts":0,"identity_verified":0,"identity_review_required":1,"identity_conflicts":0,"completeness_reconciled":0,"incomplete":0,"completeness_conflicts":0}
    def cursor(self,row_factory=None): return FakeCursor(self)
    def execute(self,sql): self.queries.append((sql,None))
    def __enter__(self): return self
    def __exit__(self,*args): return False


def test_inventory_is_read_only_and_reports_scope_coverage():
    connection=FakeConnection()
    report=MODULE.inventory(connection)
    assert report["read_only"] is True
    assert report["provider_requests"]==0
    assert report["migration_readiness"] is True
    scope=report["approvals"][0]["competition_scopes"][0]
    assert scope["competition_coverage"]["provenance_complete"]==1
    assert scope["competition_coverage"]["canonical_linked_competitions"]==1
    assert scope["fixture_coverage"]["fixture_rows"]==3
    assert scope["team_coverage"]["provenance_complete_teams"]==2
    assert scope["team_coverage"]["canonical_linked_teams"]==2
    assert scope["canonical_fixture_links"]["identity_review_required"]==1
    assert scope["canonical_fixture_links"]["source_link_review_required"]==1
    assert scope["unresolved_linked_review_cases"]==2
    assert scope["review_case_breakdown"][0]["case_type"]=="FIXTURE_DUPLICATE_CANDIDATE"
    assert report["unlinked_global_review_cases"][0]["case_type"]=="PIT_TIMESTAMP_GAP"
    assert any("competition_rows" in sql for sql,_ in connection.queries)
    assert any("primary_team_identity_link_id" in sql and "competition_identity_link_id" in sql for sql,_ in connection.queries)
    assert all("INSERT" not in sql.upper() and "UPDATE " not in sql.upper() and "DELETE " not in sql.upper() for sql,_ in connection.queries)


def test_missing_migration_fails_readiness():
    connection=FakeConnection()
    connection.migrations.remove("015_automated_identity_adjudication.sql")
    report=MODULE.inventory(connection)
    assert report["migration_readiness"] is False
    assert "015_automated_identity_adjudication.sql" in report["missing_required_migrations"]


def test_nonapproved_scope_is_reported_without_coverage_query():
    connection=FakeConnection()
    connection.approvals[0]["effective_status"]="REVOKED"
    report=MODULE.inventory(connection)
    scope=report["approvals"][0]["competition_scopes"][0]
    assert scope["eligible"] is False
    assert scope["reason"]=="APPROVAL_NOT_EFFECTIVELY_APPROVED_OR_OUTSIDE_VALIDITY"
    assert not any("fixture_rows" in sql for sql,_ in connection.queries)
