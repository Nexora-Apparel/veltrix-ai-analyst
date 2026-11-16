"""Resumable, quota-bounded historical fixture ingestion.

This module deliberately supports one reviewed competition scope only. Every
provider page is reserved before HTTP, persisted with raw response provenance,
and checkpointed before the adapter advances to the next page.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import psycopg

from app.db.request_budget import PostgresRequestBudget, RequestBudgetExceeded
from app.db.store import PostgresIngestionStore
from app.providers.approvals import FIVEDOLLAR_COMMUNITY_APPROVAL
from app.providers.collection_plan import DateWindow, build_date_windows
from app.providers.contracts import ProviderCompetition, ProviderFixture, SourceProvenance
from app.providers.five_dollar import (
    FiveDollarFootballProvider,
    ProviderAPIError,
    ProviderRateLimitError,
)
from app.providers.rights import SourceApproval

EXPECTED_DATABASE_NAME = "veltrix_ai_analyst"
COMPETITION_ID = "522514093"
SOURCE_ID = "5dollarfootballapi"
PROVIDER_NAME = "5DollarFootballAPI"
BOUNDARY_START = datetime(2026, 3, 21, tzinfo=UTC)
BOUNDARY_END = datetime(2026, 11, 9, tzinfo=UTC)
REQUEST_BUDGET = 40
IMPORTER_VERSION = "brazil-serie-b-resumable-v1"
IMPORT_APPROVAL = replace(
    FIVEDOLLAR_COMMUNITY_APPROVAL,
    approval_id="approval-5dollar-ai-analyst-historical-2026-11-16",
)
SCHEMA_VERSION = "5dollar-fixture-v1"


class HistoricalImportError(RuntimeError):
    """Raised when the historical import cannot safely continue."""


class FixturePagePersister:
    """Persist one validated API page and its checkpoint in a single transaction."""

    def __init__(
        self,
        connection: psycopg.Connection[Any],
        *,
        import_run_id: int,
        approval: SourceApproval,
        window: DateWindow,
    ) -> None:
        self.connection = connection
        self.store = PostgresIngestionStore(connection)
        self.import_run_id = import_run_id
        self.approval = approval
        self.window = window
        checkpoint = next(
            (
                item
                for item in self.store.load_checkpoints(import_run_id=import_run_id)
                if item["window_start"] == window.start_at
                and item["window_end"] == window.end_at
            ),
            None,
        )
        self.records_seen = int(checkpoint["records_seen"]) if checkpoint else 0
        self.records_inserted = int(checkpoint["records_inserted"]) if checkpoint else 0
        self.requests_used = int(checkpoint["requests_used"]) if checkpoint else 0
        self.response_hashes: list[str] = []

    @staticmethod
    def _quota_int(headers: dict[str, Any], key: str) -> int | None:
        value = headers.get(key) or headers.get(key.title())
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def _persist_team(
        self,
        fixture: ProviderFixture,
        *,
        team_id: str,
        team_name: str | None,
        response_id: int,
    ) -> None:
        if not team_name:
            raise HistoricalImportError("TEAM_NAME_MISSING; refusing incomplete entity write")
        now = fixture.provenance.retrieved_at
        payload = {"team_id": team_id, "team_name": team_name}
        observation_id = self.store.record_source_observation(
            self.approval,
            scope_value=COMPETITION_ID,
            data_type="team_catalogue",
            entity_type="team",
            provider_entity_id=team_id,
            schema_version="5dollar-team-v1",
            retrieved_at=now,
            payload=payload,
            provider_response_id=response_id,
        )
        self.store.upsert_provider_team(
            source_id=SOURCE_ID,
            competition_id=COMPETITION_ID,
            provider_team_id=team_id,
            name=team_name,
            source_observation_id=observation_id,
            approval=self.approval,
            first_seen_at=now,
            last_seen_at=now,
        )

    def _persist_fixture(self, fixture: ProviderFixture, response_id: int) -> None:
        if fixture.competition_id != COMPETITION_ID:
            raise HistoricalImportError("FIXTURE_COMPETITION_SCOPE_MISMATCH")
        if not self.window.start_at <= fixture.kickoff_at < self.window.end_at:
            raise HistoricalImportError("FIXTURE_OUTSIDE_REQUEST_WINDOW")
        now = fixture.provenance.retrieved_at
        competition = ProviderCompetition(
            provenance=SourceProvenance(
                provider=PROVIDER_NAME,
                provider_record_id=COMPETITION_ID,
                retrieved_at=now,
            ),
            competition_id=COMPETITION_ID,
            name=fixture.competition_name or f"Competition {COMPETITION_ID}",
            seasons=(fixture.season_id,) if fixture.season_id else (),
        )
        competition_observation = self.store.record_source_observation(
            self.approval,
            scope_value=COMPETITION_ID,
            data_type="competition_catalogue",
            entity_type="competition",
            provider_entity_id=COMPETITION_ID,
            schema_version="5dollar-competition-v1",
            retrieved_at=now,
            payload=competition.model_dump(mode="json"),
            provider_response_id=response_id,
        )
        self.store.upsert_provider_competition(
            competition,
            source_id=SOURCE_ID,
            source_observation_id=competition_observation,
            approval=self.approval,
        )
        self._persist_team(
            fixture,
            team_id=fixture.home_team_id,
            team_name=fixture.home_team_name,
            response_id=response_id,
        )
        self._persist_team(
            fixture,
            team_id=fixture.away_team_id,
            team_name=fixture.away_team_name,
            response_id=response_id,
        )
        observation_id = self.store.record_source_observation(
            self.approval,
            scope_value=COMPETITION_ID,
            data_type="fixtures_and_results",
            entity_type="fixture",
            provider_entity_id=fixture.provenance.provider_record_id,
            schema_version=SCHEMA_VERSION,
            retrieved_at=now,
            source_event_time=fixture.kickoff_at,
            availability_basis="RETRIEVED_AT_ONLY",
            point_in_time_certifiable=False,
            payload=fixture.model_dump(mode="json"),
            provider_response_id=response_id,
        )
        self.store.upsert_provider_fixture(
            fixture,
            source_id=SOURCE_ID,
            source_observation_id=observation_id,
            approval=self.approval,
        )

    def __call__(self, page: dict[str, Any]) -> None:
        raw_body = bytes(page["raw_body"])
        if not raw_body:
            raise HistoricalImportError("EMPTY_PROVIDER_RESPONSE_BODY")
        fetched_at = page["fetched_at"]
        request_id = str(page["response_headers"].get("x-request-id") or uuid4().hex)
        response_hash = hashlib.sha256(raw_body).hexdigest()
        with self.connection.transaction():
            response_id = self.store.record_provider_response(
                self.approval,
                scope_value=COMPETITION_ID,
                data_type="fixtures_and_results",
                endpoint=str(page["endpoint"]),
                request_id=request_id,
                request_params=dict(page["request_params"]),
                http_status=int(page["http_status"]),
                raw_body=raw_body,
                response_headers=dict(page["response_headers"]),
                fetched_at=fetched_at,
                quota_limit=self._quota_int(dict(page["response_headers"]), "x-ratelimit-limit"),
                quota_remaining=self._quota_int(
                    dict(page["response_headers"]), "x-ratelimit-remaining"
                ),
            )
            self.store.record_provider_request_event(
                self.approval,
                scope_value=COMPETITION_ID,
                data_type="fixtures_and_results",
                endpoint=str(page["endpoint"]),
                request_params=dict(page["request_params"]),
                started_at=page["request_started_at"],
                finished_at=fetched_at,
                http_status=int(page["http_status"]),
                quota_remaining=self._quota_int(
                    dict(page["response_headers"]), "x-ratelimit-remaining"
                ),
                provider_response_id=response_id,
            )
            fixtures = tuple(page["fixtures"])
            for fixture in fixtures:
                self._persist_fixture(fixture, response_id)
            self.records_seen += len(fixtures)
            self.records_inserted += len(fixtures)
            self.requests_used += 1
            self.response_hashes.append(response_hash)
            has_more = bool(page["has_more"])
            self.store.save_checkpoint(
                import_run_id=self.import_run_id,
                window_start=self.window.start_at,
                window_end=self.window.end_at,
                status="RUNNING" if has_more else "COMPLETED",
                records_seen=self.records_seen,
                records_inserted=self.records_inserted,
                requests_used=self.requests_used,
                cursor_value=str(int(page["page_number"]) + 1) if has_more else None,
                response_sha256=response_hash,
            )


def _ensure_run_checkpoints(
    store: PostgresIngestionStore,
    *,
    import_run_id: int,
    windows: tuple[DateWindow, ...],
) -> list[dict[str, Any]]:
    existing = store.load_checkpoints(import_run_id=import_run_id)
    known = {(item["window_start"], item["window_end"]) for item in existing}
    for window in windows:
        if (window.start_at, window.end_at) not in known:
            store.save_checkpoint(
                import_run_id=import_run_id,
                window_start=window.start_at,
                window_end=window.end_at,
                status="PENDING",
            )
    return store.load_checkpoints(import_run_id=import_run_id)


def _run_totals(
    connection: psycopg.Connection[Any], import_run_id: int
) -> tuple[int, int, int, int, int]:
    row = connection.execute(
        """
        SELECT
            COALESCE(SUM(records_seen), 0),
            COALESCE(SUM(records_inserted), 0),
            COALESCE(SUM(records_duplicate), 0),
            COALESCE(SUM(records_rejected), 0),
            COALESCE(SUM(records_quarantined), 0)
        FROM veltrix_ai_analyst.import_checkpoints
        WHERE import_run_id = %s
        """,
        (import_run_id,),
    ).fetchone()
    return tuple(int(value) for value in row)


def _finish(
    connection: psycopg.Connection[Any],
    *,
    import_run_id: int,
    status: str,
    reason_code: str | None,
) -> None:
    store = PostgresIngestionStore(connection)
    request_count = connection.execute(
        "SELECT requests_used FROM veltrix_ai_analyst.import_runs WHERE id = %s",
        (import_run_id,),
    ).fetchone()[0]
    seen, inserted, duplicate, rejected, quarantined = _run_totals(
        connection, import_run_id
    )
    checkpoints = store.load_checkpoints(import_run_id=import_run_id)
    manifest = hashlib.sha256(
        json.dumps(
            [
                {
                    "start": item["window_start"].isoformat(),
                    "end": item["window_end"].isoformat(),
                    "status": item["status"],
                    "cursor": item["cursor_value"],
                    "response_sha256": item["response_sha256"],
                }
                for item in checkpoints
            ],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    store.finish_import_run(
        import_run_id=import_run_id,
        status=status,
        finished_at=datetime.now(UTC),
        requests_used=int(request_count),
        records_seen=seen,
        records_inserted=inserted,
        records_duplicate=duplicate,
        records_rejected=rejected,
        records_quarantined=quarantined,
        manifest_sha256=manifest,
        reason_code=reason_code,
    )


async def run_brazil_serie_b_historical_import(
    database_url: str,
    *,
    api_key: str,
    execute: bool = False,
    import_run_id: int | None = None,
    approval: SourceApproval = IMPORT_APPROVAL,
    provider: FiveDollarFootballProvider | None = None,
) -> int:
    """Run or resume the fixed, non-commercial Brazil Serie B historical import.

    Live HTTP requires both an explicit execute=True argument and the
    VELTRIX_ENABLE_HISTORICAL_COLLECTION=true environment gate.
    """
    if not execute or os.getenv("VELTRIX_ENABLE_HISTORICAL_COLLECTION") != "true":
        raise HistoricalImportError("LIVE_COLLECTION_NOT_EXPLICITLY_ENABLED")
    if not api_key.strip():
        raise HistoricalImportError("FIVEDOLLAR_COMMUNITY_API_KEY_REQUIRED")
    if approval.approval_id != IMPORT_APPROVAL.approval_id:
        raise HistoricalImportError("UNRECOGNIZED_SOURCE_APPROVAL")
    if COMPETITION_ID not in approval.scope_values:
        raise HistoricalImportError("COMPETITION_NOT_IN_APPROVED_SOURCE_SCOPE")

    windows = build_date_windows(BOUNDARY_START, BOUNDARY_END, window_days=7)
    with psycopg.connect(database_url) as connection:
        database_name = connection.execute("SELECT current_database()").fetchone()[0]
        if database_name != EXPECTED_DATABASE_NAME:
            raise HistoricalImportError("EXPECTED_DATABASE_IDENTITY_MISMATCH")
        store = PostgresIngestionStore(connection)
        if import_run_id is None:
            import_run_id = store.create_import_run(
                approval,
                scope_value=COMPETITION_ID,
                data_type="fixtures_and_results",
                import_type="historical_backfill",
                boundary_start=BOUNDARY_START,
                boundary_end=BOUNDARY_END,
                request_budget=REQUEST_BUDGET,
                importer_version=IMPORTER_VERSION,
                started_at=datetime.now(UTC),
            )
        else:
            row = connection.execute(
                """
                SELECT status, request_budget, requests_used, boundary_start, boundary_end,
                       provider, source_id, rights_approval_id
                FROM veltrix_ai_analyst.import_runs
                WHERE id = %s
                """,
                (import_run_id,),
            ).fetchone()
            expected = (
                BOUNDARY_START,
                BOUNDARY_END,
                PROVIDER_NAME,
                SOURCE_ID,
                approval.approval_id,
            )
            if (
                row is None
                or row[1] != REQUEST_BUDGET
                or int(row[2]) > REQUEST_BUDGET
                or tuple(row[3:]) != expected
            ):
                raise HistoricalImportError("IMPORT_RUN_IDENTITY_OR_ENVELOPE_MISMATCH")
            if row[0] not in {"PAUSED", "RUNNING"}:
                raise HistoricalImportError("IMPORT_RUN_NOT_RESUMABLE")
            connection.execute(
                """
                UPDATE veltrix_ai_analyst.import_runs
                SET status = 'RUNNING', started_at = COALESCE(started_at, NOW()),
                    finished_at = NULL, reason_code = NULL
                WHERE id = %s AND status = 'PAUSED'
                """,
                (import_run_id,),
            )
        _ensure_run_checkpoints(store, import_run_id=import_run_id, windows=windows)

    active_provider = provider or FiveDollarFootballProvider(
        api_key=api_key,
        min_request_interval_seconds=12.0,
    )
    try:
        with (
            psycopg.connect(database_url, autocommit=True) as store_connection,
            psycopg.connect(database_url, autocommit=True) as quota_connection,
        ):
            store = PostgresIngestionStore(store_connection)
            checkpoints = store.load_checkpoints(import_run_id=import_run_id)
            reserver = PostgresRequestBudget(quota_connection).callback_for_run(import_run_id)
            for window, checkpoint in zip(windows, checkpoints, strict=True):
                if checkpoint["status"] == "COMPLETED":
                    continue
                start_page = int(checkpoint["cursor_value"] or "1")
                persister = FixturePagePersister(
                    store_connection,
                    import_run_id=import_run_id,
                    approval=approval,
                    window=window,
                )
                store.save_checkpoint(
                    import_run_id=import_run_id,
                    window_start=window.start_at,
                    window_end=window.end_at,
                    status="RUNNING",
                    records_seen=persister.records_seen,
                    records_inserted=persister.records_inserted,
                    requests_used=persister.requests_used,
                    cursor_value=str(start_page),
                )
                await active_provider.fetch_fixtures(
                    window.start_at,
                    window.end_at,
                    competition_ids=[COMPETITION_ID],
                    request_reserver=reserver,
                    require_request_reservation=True,
                    response_observer=persister,
                    start_page=start_page,
                )
                refreshed = next(
                    item
                    for item in store.load_checkpoints(import_run_id=import_run_id)
                    if item["window_start"] == window.start_at
                    and item["window_end"] == window.end_at
                )
                if refreshed["status"] != "COMPLETED":
                    raise HistoricalImportError("WINDOW_DID_NOT_REACH_COMPLETED_CHECKPOINT")
            _finish(
                store_connection,
                import_run_id=import_run_id,
                status="COMPLETED",
                reason_code=None,
            )
    except Exception as exc:
        with psycopg.connect(database_url) as connection:
            row = connection.execute(
                "SELECT status FROM veltrix_ai_analyst.import_runs WHERE id = %s",
                (import_run_id,),
            ).fetchone()
            if row and row[0] in {"RUNNING", "PLANNED"}:
                _finish(
                    connection,
                    import_run_id=import_run_id,
                    status="PAUSED",
                    reason_code=f"SAFE_STOP:{type(exc).__name__}",
                )
        if isinstance(exc, (ProviderAPIError, ProviderRateLimitError, RequestBudgetExceeded)):
            raise HistoricalImportError(
                f"COLLECTION_PAUSED:{type(exc).__name__}"
            ) from None
        raise
    return int(import_run_id)
