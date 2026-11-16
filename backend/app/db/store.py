"""Rights-aware PostgreSQL writer for Stage 2 provider ingestion."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.providers.contracts import ProviderCompetition, ProviderFixture
from app.providers.rights import (
    DataUsePurpose,
    SourceApproval,
    evaluate_record_scope,
    evaluate_source_use,
)


class IngestionStoreError(RuntimeError):
    """Raised when an ingestion write fails a provenance or integrity guard."""


class RightsDenied(IngestionStoreError):
    """Raised when the current source approval does not permit a requested write."""


class EvidenceConflict(IngestionStoreError):
    """Raised when an existing immutable source approval differs from its evidence."""


class PostgresIngestionStore:
    """Write source evidence and provider projections with fail-closed rights checks.

    The caller owns the connection/transaction lifecycle. Provider-local IDs are
    preserved; this store deliberately performs no cross-provider entity matching.
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    @staticmethod
    def _require_aware(value: datetime | None, field_name: str) -> None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise IngestionStoreError(f"{field_name}_MUST_BE_TIMEZONE_AWARE")

    @staticmethod
    def _canonical_json(payload: Mapping[str, Any]) -> tuple[str, str]:
        try:
            serialized = json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError):
            raise IngestionStoreError("PAYLOAD_MUST_BE_FINITE_JSON") from None
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return serialized, digest

    @staticmethod
    def _reject_sensitive_request_params(value: Any) -> None:
        forbidden = {
            "api_key",
            "apikey",
            "authorization",
            "access_token",
            "token",
            "password",
            "secret",
            "client_secret",
        }
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized = str(key).strip().casefold().replace("-", "_")
                if normalized in forbidden:
                    raise IngestionStoreError("SENSITIVE_REQUEST_PARAMETER_REJECTED")
                PostgresIngestionStore._reject_sensitive_request_params(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                PostgresIngestionStore._reject_sensitive_request_params(child)

    @staticmethod
    def _safe_response_headers(headers: Mapping[str, Any] | None) -> dict[str, str]:
        allowed = {
            "content-type",
            "date",
            "retry-after",
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "x-request-id",
        }
        safe: dict[str, str] = {}
        for key, value in (headers or {}).items():
            normalized = str(key).strip().casefold()
            if normalized in allowed and value is not None:
                safe[normalized] = str(value)[:500]
        return safe

    def sync_source_approval(self, approval: SourceApproval) -> str:
        """Insert an immutable approval once; reject changes under the same ID."""
        scope_values = sorted(approval.scope_values)
        data_types = sorted(approval.data_types)
        permitted_uses = sorted(use.value for use in approval.permitted_uses)
        expected = (
            approval.provider,
            approval.source_id,
            approval.scope_type,
            scope_values,
            data_types,
            approval.status.value,
            approval.rights_basis,
            approval.terms_url,
            approval.terms_version,
            approval.evidence_uri,
            approval.evidence_sha256,
            approval.reviewed_at_utc,
            approval.reviewer_id,
            approval.valid_from_utc,
            approval.valid_until_utc,
            permitted_uses,
            approval.commercial_use_allowed,
            approval.attribution_required,
            approval.attribution_text,
            approval.attribution_url,
            approval.raw_redistribution_allowed,
        )
        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.source_approvals (
                approval_id, provider, source_id, scope_type, scope_values, data_types,
                status, rights_basis, terms_url, terms_version, evidence_uri,
                evidence_sha256, reviewed_at, reviewer_id, valid_from, valid_until,
                permitted_uses, commercial_use_allowed, attribution_required,
                attribution_text, attribution_url, raw_redistribution_allowed
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (approval_id) DO NOTHING
            RETURNING approval_id
            """,
            (
                approval.approval_id,
                approval.provider,
                approval.source_id,
                approval.scope_type,
                Jsonb(scope_values),
                Jsonb(data_types),
                approval.status.value,
                approval.rights_basis,
                approval.terms_url,
                approval.terms_version,
                approval.evidence_uri,
                approval.evidence_sha256,
                approval.reviewed_at_utc,
                approval.reviewer_id,
                approval.valid_from_utc,
                approval.valid_until_utc,
                Jsonb(permitted_uses),
                approval.commercial_use_allowed,
                approval.attribution_required,
                approval.attribution_text,
                approval.attribution_url,
                approval.raw_redistribution_allowed,
            ),
        ).fetchone()

        if inserted is not None:
            return approval.approval_id

        existing = self.connection.execute(
            """
            SELECT provider, source_id, scope_type, scope_values, data_types,
                   status, rights_basis, terms_url, terms_version, evidence_uri,
                   evidence_sha256, reviewed_at, reviewer_id, valid_from, valid_until,
                   permitted_uses, commercial_use_allowed, attribution_required,
                   attribution_text, attribution_url, raw_redistribution_allowed
            FROM veltrix_ai_analyst.source_approvals
            WHERE approval_id = %s
            """,
            (approval.approval_id,),
        ).fetchone()
        if existing is not None:
            existing_values = list(existing)
            existing_values[10] = str(existing_values[10]).strip()
        else:
            existing_values = []
        if tuple(existing_values) != expected:
            raise EvidenceConflict("SOURCE_APPROVAL_ID_ALREADY_EXISTS_WITH_DIFFERENT_EVIDENCE")
        return approval.approval_id

    def _assert_effective_approval(self, approval_id: str, at_utc: datetime) -> None:
        self._require_aware(at_utc, "RIGHTS_EVALUATION_TIME")
        row = self.connection.execute(
            """
            SELECT
                approval.valid_from,
                approval.valid_until,
                COALESCE(
                    (
                        SELECT event.status
                        FROM veltrix_ai_analyst.source_approval_status_events AS event
                        WHERE event.approval_id = approval.approval_id
                          AND event.effective_at <= %s
                        ORDER BY event.effective_at DESC, event.id DESC
                        LIMIT 1
                    ),
                    approval.status
                ) AS effective_status
            FROM veltrix_ai_analyst.source_approvals AS approval
            WHERE approval.approval_id = %s
            """,
            (at_utc, approval_id),
        ).fetchone()
        if row is None:
            raise RightsDenied("SOURCE_APPROVAL_NOT_REGISTERED")
        valid_from, valid_until, effective_status = row
        if effective_status != "APPROVED":
            raise RightsDenied("SOURCE_RIGHTS_NOT_EFFECTIVE")
        if at_utc < valid_from or (valid_until is not None and at_utc >= valid_until):
            raise RightsDenied("SOURCE_APPROVAL_OUTSIDE_VALIDITY_WINDOW")

    def _authorize(
        self,
        approval: SourceApproval,
        *,
        scope_value: str,
        data_type: str,
        purpose: DataUsePurpose,
        at_utc: datetime,
    ) -> None:
        self.sync_source_approval(approval)
        scope_decision = evaluate_record_scope(
            approval,
            provider=approval.provider,
            source_id=approval.source_id,
            scope_type=approval.scope_type,
            scope_value=scope_value,
            data_type=data_type,
            at_utc=at_utc,
        )
        use_decision = evaluate_source_use(
            approval,
            purpose,
            scope_value=scope_value,
            at_utc=at_utc,
        )
        if not scope_decision.allowed:
            raise RightsDenied(scope_decision.reason_code)
        if not use_decision.allowed:
            raise RightsDenied(use_decision.reason_code)
        self._assert_effective_approval(approval.approval_id, at_utc)

    def _assert_observation_identity(
        self,
        *,
        observation_id: int,
        approval: SourceApproval,
        data_type: str,
        entity_type: str,
        provider_entity_id: str,
    ) -> None:
        row = self.connection.execute(
            """
            SELECT provider, source_id, data_type, entity_type,
                   provider_entity_id, rights_approval_id
            FROM veltrix_ai_analyst.source_observations
            WHERE id = %s
            """,
            (observation_id,),
        ).fetchone()
        expected = (
            approval.provider,
            approval.source_id,
            data_type,
            entity_type,
            provider_entity_id,
            approval.approval_id,
        )
        if row is None or tuple(row) != expected:
            raise IngestionStoreError("SOURCE_OBSERVATION_IDENTITY_MISMATCH")

    def record_provider_response(
        self,
        approval: SourceApproval,
        *,
        scope_value: str,
        data_type: str,
        endpoint: str,
        request_id: str,
        request_params: Mapping[str, Any],
        http_status: int,
        raw_body: bytes,
        response_headers: Mapping[str, Any] | None,
        fetched_at: datetime,
        quota_limit: int | None = None,
        quota_remaining: int | None = None,
        quota_reset_at: datetime | None = None,
        retention_until: datetime | None = None,
    ) -> int:
        """Persist exact response bytes without credentials or unsafe headers."""
        self._require_aware(fetched_at, "FETCHED_AT")
        self._require_aware(quota_reset_at, "QUOTA_RESET_AT")
        self._require_aware(retention_until, "RETENTION_UNTIL")
        if not endpoint.strip() or not request_id.strip() or not raw_body:
            raise IngestionStoreError("PROVIDER_RESPONSE_REQUIRED_FIELDS_MISSING")
        if not 100 <= http_status <= 599:
            raise IngestionStoreError("INVALID_HTTP_STATUS")
        self._reject_sensitive_request_params(request_params)
        self._authorize(
            approval,
            scope_value=scope_value,
            data_type=data_type,
            purpose=DataUsePurpose.COLLECTION,
            at_utc=fetched_at,
        )
        response_hash = hashlib.sha256(raw_body).hexdigest()
        safe_headers = self._safe_response_headers(response_headers)
        params_json, _ = self._canonical_json(request_params)
        headers_json, _ = self._canonical_json(safe_headers)

        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.provider_responses (
                provider, source_id, endpoint, request_id, request_params,
                http_status, response_sha256, raw_body, response_headers,
                quota_limit, quota_remaining, quota_reset_at, rights_approval_id,
                fetched_at, retention_until
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (provider, source_id, request_id, response_sha256) DO NOTHING
            RETURNING id
            """,
            (
                approval.provider,
                approval.source_id,
                endpoint,
                request_id,
                Jsonb(json.loads(params_json)),
                http_status,
                response_hash,
                raw_body,
                Jsonb(json.loads(headers_json)),
                quota_limit,
                quota_remaining,
                quota_reset_at,
                approval.approval_id,
                fetched_at,
                retention_until,
            ),
        ).fetchone()
        if inserted is not None:
            return int(inserted[0])

        existing = self.connection.execute(
            """
            SELECT id
            FROM veltrix_ai_analyst.provider_responses
            WHERE provider = %s AND source_id = %s AND request_id = %s
              AND response_sha256 = %s
            """,
            (approval.provider, approval.source_id, request_id, response_hash),
        ).fetchone()
        if existing is None:
            raise IngestionStoreError("PROVIDER_RESPONSE_IDEMPOTENCY_LOOKUP_FAILED")
        return int(existing[0])

    def record_source_observation(
        self,
        approval: SourceApproval,
        *,
        scope_value: str,
        data_type: str,
        entity_type: str,
        provider_entity_id: str,
        schema_version: str,
        retrieved_at: datetime,
        payload: Mapping[str, Any],
        availability_basis: str = "RETRIEVED_AT_ONLY",
        source_updated_at: datetime | None = None,
        source_event_time: datetime | None = None,
        source_published_at: datetime | None = None,
        available_at: datetime | None = None,
        point_in_time_certifiable: bool = False,
        provider_response_id: int | None = None,
        purpose: DataUsePurpose = DataUsePurpose.STORAGE,
    ) -> int:
        """Persist an immutable normalized observation with explicit time semantics."""
        for name, value in (
            ("RETRIEVED_AT", retrieved_at),
            ("SOURCE_UPDATED_AT", source_updated_at),
            ("SOURCE_EVENT_TIME", source_event_time),
            ("SOURCE_PUBLISHED_AT", source_published_at),
            ("AVAILABLE_AT", available_at),
        ):
            self._require_aware(value, name)
        if not entity_type.strip() or not provider_entity_id.strip() or not schema_version.strip():
            raise IngestionStoreError("SOURCE_OBSERVATION_IDENTITY_REQUIRED")
        if point_in_time_certifiable and (
            source_published_at is None or availability_basis != "SOURCE_PUBLISHED_AT"
        ):
            raise IngestionStoreError("PIT_CERTIFICATION_REQUIRES_VERIFIED_PUBLICATION_TIME")
        self._authorize(
            approval,
            scope_value=scope_value,
            data_type=data_type,
            purpose=purpose,
            at_utc=retrieved_at,
        )
        if provider_response_id is not None:
            response = self.connection.execute(
                """
                SELECT provider, source_id
                FROM veltrix_ai_analyst.provider_responses
                WHERE id = %s
                """,
                (provider_response_id,),
            ).fetchone()
            if response is None or tuple(response) != (approval.provider, approval.source_id):
                raise IngestionStoreError("PROVIDER_RESPONSE_IDENTITY_MISMATCH")

        payload_json, payload_hash = self._canonical_json(payload)
        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.source_observations (
                provider, source_id, data_type, entity_type, provider_entity_id,
                payload_sha256, schema_version, retrieved_at, source_updated_at,
                source_event_time, source_published_at, available_at,
                availability_basis, point_in_time_certifiable, rights_approval_id,
                provider_response_id, payload
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (
                provider, source_id, data_type, entity_type, provider_entity_id, payload_sha256
            ) DO NOTHING
            RETURNING id
            """,
            (
                approval.provider,
                approval.source_id,
                data_type,
                entity_type,
                provider_entity_id,
                payload_hash,
                schema_version,
                retrieved_at,
                source_updated_at,
                source_event_time,
                source_published_at,
                available_at,
                availability_basis,
                point_in_time_certifiable,
                approval.approval_id,
                provider_response_id,
                Jsonb(json.loads(payload_json)),
            ),
        ).fetchone()
        if inserted is not None:
            return int(inserted[0])

        existing = self.connection.execute(
            """
            SELECT id
            FROM veltrix_ai_analyst.source_observations
            WHERE provider = %s AND source_id = %s AND data_type = %s
              AND entity_type = %s AND provider_entity_id = %s AND payload_sha256 = %s
            """,
            (
                approval.provider,
                approval.source_id,
                data_type,
                entity_type,
                provider_entity_id,
                payload_hash,
            ),
        ).fetchone()
        if existing is None:
            raise IngestionStoreError("SOURCE_OBSERVATION_IDEMPOTENCY_LOOKUP_FAILED")
        return int(existing[0])

    def upsert_provider_competition(
        self,
        competition: ProviderCompetition,
        *,
        source_id: str,
        source_observation_id: int,
        approval: SourceApproval,
    ) -> int:
        retrieved_at = competition.provenance.retrieved_at
        self._authorize(
            approval,
            scope_value=competition.competition_id,
            data_type="competition_catalogue",
            purpose=DataUsePurpose.STORAGE,
            at_utc=retrieved_at,
        )
        if competition.provenance.provider != approval.provider or source_id != approval.source_id:
            raise RightsDenied("PROVIDER_COMPETITION_SOURCE_MISMATCH")
        self._assert_observation_identity(
            observation_id=source_observation_id,
            approval=approval,
            data_type="competition_catalogue",
            entity_type="competition",
            provider_entity_id=competition.competition_id,
        )
        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.provider_competitions (
                provider, source_id, provider_competition_id, name, country_code,
                country_name, seasons, is_popular, has_standings, last_fixture_at,
                source_observation_id, rights_approval_id, first_seen_at, last_seen_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (provider, source_id, provider_competition_id) DO UPDATE SET
                name = EXCLUDED.name,
                country_code = EXCLUDED.country_code,
                country_name = EXCLUDED.country_name,
                seasons = EXCLUDED.seasons,
                is_popular = EXCLUDED.is_popular,
                has_standings = EXCLUDED.has_standings,
                last_fixture_at = EXCLUDED.last_fixture_at,
                source_observation_id = EXCLUDED.source_observation_id,
                rights_approval_id = EXCLUDED.rights_approval_id,
                last_seen_at = GREATEST(
                    veltrix_ai_analyst.provider_competitions.last_seen_at,
                    EXCLUDED.last_seen_at
                )
            RETURNING id
            """,
            (
                approval.provider,
                source_id,
                competition.competition_id,
                competition.name,
                competition.country_code,
                competition.country_name,
                Jsonb(list(competition.seasons)),
                competition.is_popular,
                competition.has_standings,
                competition.last_fixture_at,
                source_observation_id,
                approval.approval_id,
                retrieved_at,
                retrieved_at,
            ),
        ).fetchone()
        if inserted is None:
            raise IngestionStoreError("PROVIDER_COMPETITION_UPSERT_FAILED")
        return int(inserted[0])

    def upsert_provider_team(
        self,
        *,
        source_id: str,
        competition_id: str,
        provider_team_id: str,
        name: str,
        source_observation_id: int,
        approval: SourceApproval,
        country_code: str | None = None,
        first_seen_at: datetime,
        last_seen_at: datetime,
    ) -> int:
        self._require_aware(first_seen_at, "FIRST_SEEN_AT")
        self._require_aware(last_seen_at, "LAST_SEEN_AT")
        self._authorize(
            approval,
            scope_value=competition_id,
            data_type="team_catalogue",
            purpose=DataUsePurpose.STORAGE,
            at_utc=last_seen_at,
        )
        if source_id != approval.source_id or not provider_team_id.strip() or not name.strip():
            raise RightsDenied("PROVIDER_TEAM_SOURCE_MISMATCH")
        self._assert_observation_identity(
            observation_id=source_observation_id,
            approval=approval,
            data_type="team_catalogue",
            entity_type="team",
            provider_entity_id=provider_team_id,
        )
        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.provider_teams (
                provider, source_id, provider_team_id, name, country_code,
                source_observation_id, rights_approval_id, first_seen_at, last_seen_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (provider, source_id, provider_team_id) DO UPDATE SET
                name = EXCLUDED.name,
                country_code = EXCLUDED.country_code,
                source_observation_id = EXCLUDED.source_observation_id,
                rights_approval_id = EXCLUDED.rights_approval_id,
                last_seen_at = GREATEST(
                    veltrix_ai_analyst.provider_teams.last_seen_at,
                    EXCLUDED.last_seen_at
                )
            RETURNING id
            """,
            (
                approval.provider,
                source_id,
                provider_team_id,
                name,
                country_code,
                source_observation_id,
                approval.approval_id,
                first_seen_at,
                last_seen_at,
            ),
        ).fetchone()
        if inserted is None:
            raise IngestionStoreError("PROVIDER_TEAM_UPSERT_FAILED")
        return int(inserted[0])

    def upsert_provider_fixture(
        self,
        fixture: ProviderFixture,
        *,
        source_id: str,
        source_observation_id: int,
        approval: SourceApproval,
    ) -> int:
        retrieved_at = fixture.provenance.retrieved_at
        self._authorize(
            approval,
            scope_value=fixture.competition_id,
            data_type="fixtures_and_results",
            purpose=DataUsePurpose.STORAGE,
            at_utc=retrieved_at,
        )
        if fixture.provenance.provider != approval.provider or source_id != approval.source_id:
            raise RightsDenied("PROVIDER_FIXTURE_SOURCE_MISMATCH")
        self._assert_observation_identity(
            observation_id=source_observation_id,
            approval=approval,
            data_type="fixtures_and_results",
            entity_type="fixture",
            provider_entity_id=fixture.provenance.provider_record_id,
        )
        inserted = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.provider_fixtures (
                provider, source_id, provider_fixture_id, provider_competition_id,
                home_team_provider_id, away_team_provider_id, home_team_name,
                away_team_name, kickoff_at, status, status_reason, status_code,
                home_goals, away_goals, home_corners, away_corners,
                home_yellow_cards, away_yellow_cards, home_red_cards, away_red_cards,
                source_observation_id, rights_approval_id, first_seen_at, last_seen_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (provider, source_id, provider_fixture_id) DO UPDATE SET
                provider_competition_id = EXCLUDED.provider_competition_id,
                home_team_provider_id = EXCLUDED.home_team_provider_id,
                away_team_provider_id = EXCLUDED.away_team_provider_id,
                home_team_name = EXCLUDED.home_team_name,
                away_team_name = EXCLUDED.away_team_name,
                kickoff_at = EXCLUDED.kickoff_at,
                status = EXCLUDED.status,
                status_reason = EXCLUDED.status_reason,
                status_code = EXCLUDED.status_code,
                home_goals = EXCLUDED.home_goals,
                away_goals = EXCLUDED.away_goals,
                home_corners = EXCLUDED.home_corners,
                away_corners = EXCLUDED.away_corners,
                home_yellow_cards = EXCLUDED.home_yellow_cards,
                away_yellow_cards = EXCLUDED.away_yellow_cards,
                home_red_cards = EXCLUDED.home_red_cards,
                away_red_cards = EXCLUDED.away_red_cards,
                source_observation_id = EXCLUDED.source_observation_id,
                rights_approval_id = EXCLUDED.rights_approval_id,
                last_seen_at = GREATEST(
                    veltrix_ai_analyst.provider_fixtures.last_seen_at,
                    EXCLUDED.last_seen_at
                )
            RETURNING id
            """,
            (
                approval.provider,
                source_id,
                fixture.provenance.provider_record_id,
                fixture.competition_id,
                fixture.home_team_id,
                fixture.away_team_id,
                fixture.home_team_name,
                fixture.away_team_name,
                fixture.kickoff_at,
                fixture.status.upper(),
                fixture.status_reason,
                fixture.status_code,
                fixture.home_goals,
                fixture.away_goals,
                fixture.home_corners,
                fixture.away_corners,
                fixture.home_yellow_cards,
                fixture.away_yellow_cards,
                fixture.home_red_cards,
                fixture.away_red_cards,
                source_observation_id,
                approval.approval_id,
                retrieved_at,
                retrieved_at,
            ),
        ).fetchone()
        if inserted is None:
            raise IngestionStoreError("PROVIDER_FIXTURE_UPSERT_FAILED")
        return int(inserted[0])

    def create_import_run(
        self,
        approval: SourceApproval,
        *,
        scope_value: str,
        data_type: str,
        import_type: str,
        boundary_start: datetime,
        boundary_end: datetime,
        request_budget: int,
        importer_version: str,
        started_at: datetime | None = None,
    ) -> int:
        self._require_aware(boundary_start, "BOUNDARY_START")
        self._require_aware(boundary_end, "BOUNDARY_END")
        self._require_aware(started_at, "STARTED_AT")
        if boundary_end <= boundary_start or request_budget < 0:
            raise IngestionStoreError("INVALID_IMPORT_BOUNDARY_OR_BUDGET")
        self._authorize(
            approval,
            scope_value=scope_value,
            data_type=data_type,
            purpose=DataUsePurpose.HISTORICAL_IMPORT,
            at_utc=started_at or datetime.now(UTC),
        )
        row = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.import_runs (
                provider, source_id, import_type, boundary_start, boundary_end,
                status, importer_version, request_budget, rights_approval_id, started_at
            ) VALUES (%s, %s, %s, %s, %s, 'PLANNED', %s, %s, %s, %s)
            RETURNING id
            """,
            (
                approval.provider,
                approval.source_id,
                import_type,
                boundary_start,
                boundary_end,
                importer_version,
                request_budget,
                approval.approval_id,
                started_at,
            ),
        ).fetchone()
        if row is None:
            raise IngestionStoreError("IMPORT_RUN_CREATE_FAILED")
        return int(row[0])

    def save_checkpoint(
        self,
        *,
        import_run_id: int,
        window_start: datetime,
        window_end: datetime,
        status: str,
        records_seen: int = 0,
        records_inserted: int = 0,
        records_duplicate: int = 0,
        records_rejected: int = 0,
        records_quarantined: int = 0,
        requests_used: int = 0,
        cursor_value: str | None = None,
        response_sha256: str | None = None,
        last_error_code: str | None = None,
    ) -> None:
        self._require_aware(window_start, "WINDOW_START")
        self._require_aware(window_end, "WINDOW_END")
        self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.import_checkpoints (
                import_run_id, window_start, window_end, cursor_value, status,
                records_seen, records_inserted, records_duplicate, records_rejected,
                records_quarantined, requests_used, response_sha256, last_error_code,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (import_run_id, window_start, window_end) DO UPDATE SET
                cursor_value = EXCLUDED.cursor_value,
                status = EXCLUDED.status,
                records_seen = EXCLUDED.records_seen,
                records_inserted = EXCLUDED.records_inserted,
                records_duplicate = EXCLUDED.records_duplicate,
                records_rejected = EXCLUDED.records_rejected,
                records_quarantined = EXCLUDED.records_quarantined,
                requests_used = EXCLUDED.requests_used,
                response_sha256 = EXCLUDED.response_sha256,
                last_error_code = EXCLUDED.last_error_code,
                updated_at = NOW()
            """,
            (
                import_run_id,
                window_start,
                window_end,
                cursor_value,
                status,
                records_seen,
                records_inserted,
                records_duplicate,
                records_rejected,
                records_quarantined,
                requests_used,
                response_sha256,
                last_error_code,
            ),
        )

    def quarantine_record(
        self,
        *,
        provider: str,
        source_id: str,
        provider_entity_id: str,
        reason_code: str,
        details: Mapping[str, Any],
        source_observation_id: int | None = None,
        import_run_id: int | None = None,
    ) -> int:
        details_json, _ = self._canonical_json(details)
        row = self.connection.execute(
            """
            INSERT INTO veltrix_ai_analyst.ingestion_quarantine (
                provider, source_id, provider_entity_id, source_observation_id,
                import_run_id, reason_code, details
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                provider,
                source_id,
                provider_entity_id,
                source_observation_id,
                import_run_id,
                reason_code,
                Jsonb(json.loads(details_json)),
            ),
        ).fetchone()
        if row is None:
            raise IngestionStoreError("QUARANTINE_RECORD_CREATE_FAILED")
        return int(row[0])
