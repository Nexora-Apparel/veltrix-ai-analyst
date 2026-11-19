"""Provenance-preserving canonical materialization for approved source scopes.

The default Brazil Serie B run-3 operation is read-only. Writes require an
explicit execute=True call inside a caller-owned PostgreSQL connection.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class CanonicalMaterializationScope:
    provider: str
    source_id: str
    competition_id: str
    rights_approval_id: str
    import_run_id: int | None
    expected_fixture_count: int | None = None
    expected_team_count: int | None = None
    identity_collision_team_alias_pairs: tuple[tuple[str, str], ...] = ()


BRAZIL_SERIE_B_RUN_3 = CanonicalMaterializationScope(
    provider="5DollarFootballAPI",
    source_id="5dollarfootballapi",
    competition_id="522514093",
    rights_approval_id="approval-5dollar-community-fixtures-2026-11-12",
    import_run_id=3,
    expected_fixture_count=374,
    expected_team_count=21,
    identity_collision_team_alias_pairs=(("1102583842", "3808811746"),),
)

IDENTITY_COLLISION_WINDOW = timedelta(minutes=2)


@dataclass(frozen=True)
class CanonicalMaterializationPlan:
    provider: str
    source_id: str
    competition_id: str
    import_run_id: int | None
    team_count: int
    competition_count: int
    fixture_count: int
    finished_fixture_count: int
    unknown_fixture_count: int
    provenance_complete_team_count: int
    provenance_complete_competition_count: int
    provenance_complete_fixture_count: int
    non_pit_observation_count: int
    conflict_fixture_ids: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.blockers

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "source_id": self.source_id,
            "competition_id": self.competition_id,
            "import_run_id": self.import_run_id,
            "team_count": self.team_count,
            "competition_count": self.competition_count,
            "fixture_count": self.fixture_count,
            "finished_fixture_count": self.finished_fixture_count,
            "unknown_fixture_count": self.unknown_fixture_count,
            "provenance_complete_team_count": self.provenance_complete_team_count,
            "provenance_complete_competition_count": (
                self.provenance_complete_competition_count
            ),
            "provenance_complete_fixture_count": self.provenance_complete_fixture_count,
            "non_pit_observation_count": self.non_pit_observation_count,
            "conflict_fixture_ids": list(self.conflict_fixture_ids),
            "blockers": list(self.blockers),
            "ready": self.ready,
        }


class CanonicalMaterializationError(RuntimeError):
    """Raised when source evidence is incomplete or an existing mapping drifts."""


def _rows(
    connection: psycopg.Connection[Any], sql: str, params: tuple[Any, ...] = ()
) -> list[dict[str, Any]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return list(cursor.fetchall())


def _one(
    connection: psycopg.Connection[Any], sql: str, params: tuple[Any, ...] = ()
) -> dict[str, Any] | None:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _run_response_predicate(scope: CanonicalMaterializationScope) -> str:
    if scope.import_run_id is None:
        return "TRUE"
    return """
        EXISTS (
            SELECT 1
            FROM veltrix_ai_analyst.source_observation_sightings run_sighting
            JOIN veltrix_ai_analyst.import_request_reservations reservation
              ON reservation.provider_response_id = run_sighting.provider_response_id
            WHERE run_sighting.source_observation_id = observation.id
              AND reservation.import_run_id = %s
        )
    """


def _load_candidates(
    connection: psycopg.Connection[Any], scope: CanonicalMaterializationScope
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    approval = _one(
        connection,
        """
        SELECT approval.status, approval.valid_from, approval.valid_until,
               approval.scope_type, approval.scope_values, approval.data_types,
               approval.permitted_uses,
               COALESCE(latest.status, approval.status) AS effective_status
        FROM veltrix_ai_analyst.source_approvals approval
        LEFT JOIN LATERAL (
            SELECT event.status
            FROM veltrix_ai_analyst.source_approval_status_events event
            WHERE event.approval_id = approval.approval_id
              AND event.effective_at <= statement_timestamp()
            ORDER BY event.effective_at DESC, event.id DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE approval.approval_id = %s
          AND approval.provider = %s
          AND approval.source_id = %s
        """,
        (scope.rights_approval_id, scope.provider, scope.source_id),
    )

    run_predicate = _run_response_predicate(scope)
    run_params: tuple[Any, ...] = () if scope.import_run_id is None else (scope.import_run_id,)

    competition = _one(
        connection,
        f"""
        SELECT source.provider_competition_id, source.name, source.source_observation_id,
               source.rights_approval_id, observation.payload_sha256,
               observation.provider AS observation_provider,
               observation.source_id AS observation_source_id,
               observation.data_type, observation.entity_type, observation.provider_entity_id,
               observation.rights_approval_id AS observation_rights_approval_id,
               observation.point_in_time_certifiable,
               provenance.source_sighting_id, provenance.provider_response_id
        FROM veltrix_ai_analyst.provider_competitions source
        LEFT JOIN veltrix_ai_analyst.source_observations observation
          ON observation.id = source.source_observation_id
        LEFT JOIN LATERAL (
            SELECT sighting.id AS source_sighting_id,
                   sighting.provider_response_id
            FROM veltrix_ai_analyst.source_observation_sightings sighting
            JOIN veltrix_ai_analyst.provider_responses response
              ON response.id = sighting.provider_response_id
             AND response.provider = source.provider
             AND response.source_id = source.source_id
             AND response.rights_approval_id = source.rights_approval_id
             AND response.http_status BETWEEN 200 AND 299
            WHERE sighting.source_observation_id = observation.id
              AND sighting.payload_sha256 = observation.payload_sha256
              AND {run_predicate}
            ORDER BY sighting.retrieved_at, sighting.id
            LIMIT 1
        ) provenance ON TRUE
        WHERE source.provider = %s AND source.source_id = %s
          AND source.provider_competition_id = %s
        """,
        (*run_params, scope.provider, scope.source_id, scope.competition_id),
    )

    teams = _rows(
        connection,
        f"""
        WITH scoped_ids AS (
            SELECT source.home_team_provider_id AS provider_team_id
            FROM veltrix_ai_analyst.provider_fixtures source
            WHERE source.provider = %s AND source.source_id = %s AND source.provider_competition_id = %s
              AND ({_fixture_run_predicate(scope)})
            UNION
            SELECT source.away_team_provider_id
            FROM veltrix_ai_analyst.provider_fixtures source
            WHERE source.provider = %s AND source.source_id = %s AND source.provider_competition_id = %s
              AND ({_fixture_run_predicate(scope)})
        )
        SELECT source.provider_team_id, source.name, source.source_observation_id,
               source.rights_approval_id, observation.payload_sha256,
               observation.provider AS observation_provider,
               observation.source_id AS observation_source_id,
               observation.data_type, observation.entity_type, observation.provider_entity_id,
               observation.rights_approval_id AS observation_rights_approval_id,
               observation.point_in_time_certifiable,
               provenance.source_sighting_id, provenance.provider_response_id
        FROM scoped_ids
        JOIN veltrix_ai_analyst.provider_teams source
          ON source.provider = %s AND source.source_id = %s
         AND source.provider_team_id = scoped_ids.provider_team_id
        LEFT JOIN veltrix_ai_analyst.source_observations observation
          ON observation.id = source.source_observation_id
        LEFT JOIN LATERAL (
            SELECT sighting.id AS source_sighting_id,
                   sighting.provider_response_id
            FROM veltrix_ai_analyst.source_observation_sightings sighting
            JOIN veltrix_ai_analyst.provider_responses response
              ON response.id = sighting.provider_response_id
             AND response.provider = source.provider
             AND response.source_id = source.source_id
             AND response.rights_approval_id = source.rights_approval_id
             AND response.http_status BETWEEN 200 AND 299
            WHERE sighting.source_observation_id = observation.id
              AND sighting.payload_sha256 = observation.payload_sha256
              AND {run_predicate}
            ORDER BY sighting.retrieved_at, sighting.id
            LIMIT 1
        ) provenance ON TRUE
        ORDER BY source.provider_team_id
        """,
        (
            scope.provider, scope.source_id, scope.competition_id, *run_params,
            scope.provider, scope.source_id, scope.competition_id, *run_params,
            scope.provider, scope.source_id, *run_params,
        ),
    )

    fixtures = _rows(
        connection,
        f"""
        SELECT source.id AS provider_fixture_row_id, source.provider_fixture_id,
               source.provider_competition_id, source.home_team_provider_id,
               source.away_team_provider_id, source.kickoff_at, source.status,
               source.home_goals, source.away_goals, source.source_observation_id,
               source.rights_approval_id, observation.payload_sha256,
               observation.provider AS observation_provider,
               observation.source_id AS observation_source_id,
               observation.data_type, observation.entity_type, observation.provider_entity_id,
               observation.rights_approval_id AS observation_rights_approval_id,
               observation.point_in_time_certifiable,
               provenance.source_sighting_id, provenance.provider_response_id
        FROM veltrix_ai_analyst.provider_fixtures source
        LEFT JOIN veltrix_ai_analyst.source_observations observation
          ON observation.id = source.source_observation_id
        LEFT JOIN LATERAL (
            SELECT sighting.id AS source_sighting_id,
                   sighting.provider_response_id
            FROM veltrix_ai_analyst.source_observation_sightings sighting
            JOIN veltrix_ai_analyst.provider_responses response
              ON response.id = sighting.provider_response_id
             AND response.provider = source.provider
             AND response.source_id = source.source_id
             AND response.rights_approval_id = source.rights_approval_id
             AND response.http_status BETWEEN 200 AND 299
            WHERE sighting.source_observation_id = observation.id
              AND sighting.payload_sha256 = observation.payload_sha256
              AND {run_predicate}
            ORDER BY sighting.retrieved_at, sighting.id
            LIMIT 1
        ) provenance ON TRUE
        WHERE source.provider = %s AND source.source_id = %s
          AND source.provider_competition_id = %s
          AND ({_fixture_run_predicate(scope)})
        ORDER BY source.kickoff_at, source.id
        """,
        (
            *run_params, scope.provider, scope.source_id, scope.competition_id,
            *run_params,
        ),
    )
    return approval, teams, [competition] if competition else [], fixtures


def _fixture_run_predicate(scope: CanonicalMaterializationScope) -> str:
    if scope.import_run_id is None:
        return "TRUE"
    return """
        EXISTS (
            SELECT 1
            FROM veltrix_ai_analyst.source_observation_sightings run_sighting
            JOIN veltrix_ai_analyst.import_request_reservations reservation
              ON reservation.provider_response_id = run_sighting.provider_response_id
            WHERE run_sighting.source_observation_id = source.source_observation_id
              AND reservation.import_run_id = %s
        )
    """


def _identity_collision_fixture_ids(
    fixtures: list[dict[str, Any]],
    alias_pairs: tuple[tuple[str, str], ...] = (),
) -> tuple[str, ...]:
    """Flag exact repeated pairings or explicitly evidenced provider-ID aliases."""
    conflicts: set[str] = set()
    for index, left in enumerate(fixtures):
        left_teams = {
            str(left["home_team_provider_id"]),
            str(left["away_team_provider_id"]),
        }
        for right in fixtures[index + 1:]:
            right_teams = {
                str(right["home_team_provider_id"]),
                str(right["away_team_provider_id"]),
            }
            close_in_time = abs(left["kickoff_at"] - right["kickoff_at"]) <= IDENTITY_COLLISION_WINDOW
            same_ordered_pair = (
                left["home_team_provider_id"] == right["home_team_provider_id"]
                and left["away_team_provider_id"] == right["away_team_provider_id"]
            )
            alias_collision = False
            if close_in_time:
                for alias_a, alias_b in alias_pairs:
                    for first, second in ((alias_a, alias_b), (alias_b, alias_a)):
                        if first in left_teams and second in right_teams:
                            left_opponent = next(iter(left_teams - {first}), None)
                            right_opponent = next(iter(right_teams - {second}), None)
                            if left_opponent is not None and left_opponent == right_opponent:
                                alias_collision = True
                                break
                    if alias_collision:
                        break
            if close_in_time and (same_ordered_pair or alias_collision):
                conflicts.add(str(left["provider_fixture_id"]))
                conflicts.add(str(right["provider_fixture_id"]))
    return tuple(sorted(conflicts))


def build_brazil_serie_b_materialization_plan(
    connection: psycopg.Connection[Any],
    scope: CanonicalMaterializationScope = BRAZIL_SERIE_B_RUN_3,
) -> CanonicalMaterializationPlan:
    """Build a read-only, rights- and provenance-checked materialization plan."""
    approval, teams, competitions, fixtures = _load_candidates(connection, scope)
    blockers: list[str] = []
    now = datetime.now(UTC)

    if approval is None:
        blockers.append("SOURCE_APPROVAL_NOT_FOUND")
    else:
        if approval["effective_status"] != "APPROVED":
            blockers.append("SOURCE_APPROVAL_NOT_EFFECTIVE")
        if now < approval["valid_from"] or (
            approval["valid_until"] is not None and now >= approval["valid_until"]
        ):
            blockers.append("SOURCE_APPROVAL_OUTSIDE_VALIDITY")
        if approval["scope_type"] != "competition_id":
            blockers.append("SOURCE_APPROVAL_SCOPE_TYPE_MISMATCH")
        if scope.competition_id not in approval["scope_values"]:
            blockers.append("SOURCE_APPROVAL_SCOPE_MISMATCH")
        required_types = {"fixtures_and_results", "team_catalogue", "competition_catalogue"}
        if not required_types.issubset(set(approval["data_types"])):
            blockers.append("SOURCE_APPROVAL_DATA_TYPE_MISMATCH")
        if not {"STORAGE", "INTERNAL_ANALYSIS"}.issubset(set(approval["permitted_uses"])):
            blockers.append("SOURCE_APPROVAL_USE_NOT_PERMITTED")

    valid_team_count = 0
    for team in teams:
        if (
            team["source_observation_id"] is not None
            and team["rights_approval_id"] == scope.rights_approval_id
            and team["observation_provider"] == scope.provider
            and team["observation_source_id"] == scope.source_id
            and team["observation_rights_approval_id"] == scope.rights_approval_id
            and team["data_type"] == "team_catalogue"
            and team["entity_type"] == "team"
            and team["provider_entity_id"] == team["provider_team_id"]
            and team["payload_sha256"] is not None
            and team["source_sighting_id"] is not None
            and team["provider_response_id"] is not None
        ):
            valid_team_count += 1
    if valid_team_count != len(teams):
        blockers.append("TEAM_SOURCE_PROVENANCE_INCOMPLETE")
    if not teams:
        blockers.append("NO_SOURCE_TEAMS_FOUND")
    if scope.expected_team_count is not None and len(teams) != scope.expected_team_count:
        blockers.append("TEAM_SCOPE_COUNT_MISMATCH")

    valid_competition_count = 0
    for competition in competitions:
        if (
            competition["rights_approval_id"] == scope.rights_approval_id
            and competition["source_observation_id"] is not None
            and competition["observation_provider"] == scope.provider
            and competition["observation_source_id"] == scope.source_id
            and competition["observation_rights_approval_id"] == scope.rights_approval_id
            and competition["data_type"] == "competition_catalogue"
            and competition["entity_type"] == "competition"
            and competition["provider_entity_id"] == scope.competition_id
            and competition["payload_sha256"] is not None
            and competition["source_sighting_id"] is not None
            and competition["provider_response_id"] is not None
        ):
            valid_competition_count += 1
    if valid_competition_count != 1:
        blockers.append("COMPETITION_SOURCE_PROVENANCE_INCOMPLETE")

    valid_fixture_count = 0
    finished_count = 0
    unknown_count = 0
    non_pit_count = sum(
        not row["point_in_time_certifiable"] for row in [*teams, *competitions, *fixtures]
    )
    for fixture in fixtures:
        if (
            fixture["rights_approval_id"] == scope.rights_approval_id
            and fixture["source_observation_id"] is not None
            and fixture["observation_provider"] == scope.provider
            and fixture["observation_source_id"] == scope.source_id
            and fixture["observation_rights_approval_id"] == scope.rights_approval_id
            and fixture["data_type"] == "fixtures_and_results"
            and fixture["entity_type"] == "fixture"
            and fixture["provider_entity_id"] == fixture["provider_fixture_id"]
            and fixture["payload_sha256"] is not None
            and fixture["source_sighting_id"] is not None
            and fixture["provider_response_id"] is not None
        ):
            valid_fixture_count += 1
        if fixture["status"] == "FINISHED":
            finished_count += 1
        elif fixture["status"] == "UNKNOWN":
            unknown_count += 1
    if valid_fixture_count != len(fixtures):
        blockers.append("FIXTURE_SOURCE_PROVENANCE_INCOMPLETE")
    if not fixtures:
        blockers.append("NO_SOURCE_FIXTURES_FOUND")
    if scope.expected_fixture_count is not None and len(fixtures) != scope.expected_fixture_count:
        blockers.append("FIXTURE_SCOPE_COUNT_MISMATCH")
    if finished_count + unknown_count != len(fixtures):
        blockers.append("UNEXPECTED_FIXTURE_STATUS_PRESENT")
    if any(
        fixture["status"] == "FINISHED"
        and (fixture["home_goals"] is None or fixture["away_goals"] is None)
        for fixture in fixtures
    ):
        blockers.append("FINISHED_FIXTURE_SCORE_MISSING")
    if any(
        fixture["status"] != "FINISHED"
        and (fixture["home_goals"] is not None or fixture["away_goals"] is not None)
        for fixture in fixtures
    ):
        blockers.append("UNSETTLED_FIXTURE_HAS_SCORE")

    conflict_ids = _identity_collision_fixture_ids(fixtures, scope.identity_collision_team_alias_pairs)
    return CanonicalMaterializationPlan(
        provider=scope.provider,
        source_id=scope.source_id,
        competition_id=scope.competition_id,
        import_run_id=scope.import_run_id,
        team_count=len(teams),
        competition_count=len(competitions),
        fixture_count=len(fixtures),
        finished_fixture_count=finished_count,
        unknown_fixture_count=unknown_count,
        provenance_complete_team_count=valid_team_count,
        provenance_complete_competition_count=valid_competition_count,
        provenance_complete_fixture_count=valid_fixture_count,
        non_pit_observation_count=non_pit_count,
        conflict_fixture_ids=conflict_ids,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def materialize_brazil_serie_b_canonical_entities(
    connection: psycopg.Connection[Any],
    *,
    execute: bool = False,
    scope: CanonicalMaterializationScope = BRAZIL_SERIE_B_RUN_3,
) -> dict[str, Any]:
    """Preview by default; write canonical source placeholders only with execute=True."""
    if not execute:
        return {"mode": "DRY_RUN", "plan": build_brazil_serie_b_materialization_plan(connection, scope).as_dict()}

    with connection.transaction():
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"veltrix-canonical:{scope.provider}:{scope.source_id}:{scope.competition_id}:{scope.import_run_id}",),
        )
        approval, teams, competitions, fixtures = _load_candidates(connection, scope)
        plan = build_brazil_serie_b_materialization_plan(connection, scope)
        if not plan.ready:
            raise CanonicalMaterializationError(",".join(plan.blockers))
        if approval is None or len(competitions) != 1:
            raise CanonicalMaterializationError("CANONICAL_SOURCE_SCOPE_NOT_UNIQUE")

        competition = competitions[0]
        existing_competition = _one(
            connection,
            """
            SELECT link.canonical_competition_id, canonical.display_name,
                   canonical.identity_basis, link.source_observation_id, link.source_sighting_id,
                   link.provider_response_id, link.rights_approval_id, link.payload_sha256,
                   link.mapping_method, link.mapping_status
            FROM veltrix_ai_analyst.provider_competition_identity_links link
            JOIN veltrix_ai_analyst.canonical_competitions canonical
              ON canonical.id = link.canonical_competition_id
            WHERE link.provider = %s AND link.source_id = %s
              AND link.provider_competition_id = %s
            """,
            (scope.provider, scope.source_id, scope.competition_id),
        )
        if existing_competition:
            expected = (
                competition["name"], "SOURCE_LOCAL_ONLY", competition["source_observation_id"],
                competition["source_sighting_id"], competition["provider_response_id"],
                scope.rights_approval_id, competition["payload_sha256"],
                "EXACT_PROVIDER_ID", "REVIEW_REQUIRED",
            )
            actual = (
                existing_competition["display_name"], existing_competition["identity_basis"],
                existing_competition["source_observation_id"], existing_competition["source_sighting_id"],
                existing_competition["provider_response_id"], existing_competition["rights_approval_id"],
                existing_competition["payload_sha256"].strip(), existing_competition["mapping_method"],
                existing_competition["mapping_status"],
            )
            if actual != expected:
                raise CanonicalMaterializationError("EXISTING_COMPETITION_MAPPING_DRIFT")
            canonical_competition_id = existing_competition["canonical_competition_id"]
            competition_created = False
        else:
            canonical_competition_id = connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.canonical_competitions
                    (display_name, identity_basis)
                VALUES (%s, 'SOURCE_LOCAL_ONLY')
                RETURNING id
                """,
                (competition["name"],),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.provider_competition_identity_links (
                    provider, source_id, provider_competition_id, canonical_competition_id,
                    source_observation_id, source_sighting_id, provider_response_id,
                    rights_approval_id, payload_sha256, mapping_method, mapping_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXACT_PROVIDER_ID', 'REVIEW_REQUIRED')
                """,
                (
                    scope.provider, scope.source_id, scope.competition_id,
                    canonical_competition_id, competition["source_observation_id"],
                    competition["source_sighting_id"], competition["provider_response_id"],
                    scope.rights_approval_id, competition["payload_sha256"],
                ),
            )
            competition_created = True

        canonical_team_ids: dict[str, Any] = {}
        created_teams = 0
        for team in teams:
            existing = _one(
                connection,
                """
                SELECT link.canonical_team_id, canonical.display_name, canonical.identity_basis,
                       link.source_observation_id, link.source_sighting_id,
                       link.provider_response_id, link.rights_approval_id, link.payload_sha256,
                       link.mapping_method, link.mapping_status
                FROM veltrix_ai_analyst.provider_team_identity_links link
                JOIN veltrix_ai_analyst.canonical_teams canonical
                  ON canonical.id = link.canonical_team_id
                WHERE link.provider = %s AND link.source_id = %s
                  AND link.provider_team_id = %s
                """,
                (scope.provider, scope.source_id, team["provider_team_id"]),
            )
            if existing:
                expected = (
                    team["name"], "SOURCE_LOCAL_ONLY", team["source_observation_id"],
                    team["source_sighting_id"], team["provider_response_id"], scope.rights_approval_id,
                    team["payload_sha256"], "EXACT_PROVIDER_ID", "REVIEW_REQUIRED",
                )
                actual = (
                    existing["display_name"], existing["identity_basis"], existing["source_observation_id"],
                    existing["source_sighting_id"], existing["provider_response_id"],
                    existing["rights_approval_id"], existing["payload_sha256"].strip(),
                    existing["mapping_method"], existing["mapping_status"],
                )
                if actual != expected:
                    raise CanonicalMaterializationError(
                        f"EXISTING_TEAM_MAPPING_DRIFT:{team['provider_team_id']}"
                    )
                canonical_team_ids[team["provider_team_id"]] = existing["canonical_team_id"]
            else:
                canonical_id = connection.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.canonical_teams
                        (display_name, identity_basis)
                    VALUES (%s, 'SOURCE_LOCAL_ONLY')
                    RETURNING id
                    """,
                    (team["name"],),
                ).fetchone()[0]
                connection.execute(
                    """
                    INSERT INTO veltrix_ai_analyst.provider_team_identity_links (
                        provider, source_id, provider_team_id, canonical_team_id,
                        source_observation_id, source_sighting_id, provider_response_id,
                        rights_approval_id, payload_sha256, mapping_method, mapping_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'EXACT_PROVIDER_ID', 'REVIEW_REQUIRED')
                    """,
                    (
                        scope.provider, scope.source_id, team["provider_team_id"],
                        canonical_id, team["source_observation_id"], team["source_sighting_id"],
                        team["provider_response_id"], scope.rights_approval_id,
                        team["payload_sha256"],
                    ),
                )
                canonical_team_ids[team["provider_team_id"]] = canonical_id
                created_teams += 1

        created_fixtures = 0
        reused_fixtures = 0
        conflict_ids = set(plan.conflict_fixture_ids)
        for fixture in fixtures:
            existing = _one(
                connection,
                """
                SELECT source.canonical_fixture_id, canonical.kickoff_at, canonical.status,
                       canonical.home_goals, canonical.away_goals,
                       canonical.canonical_competition_id, canonical.home_canonical_team_id,
                       canonical.away_canonical_team_id, canonical.identity_status,
                       canonical.completeness_status, source.provider, source.source_id, source.provider_fixture_id,
                       source.source_observation_id, source.source_sighting_id,
                       source.provider_response_id, source.rights_approval_id,
                       source.payload_sha256, source.mapping_method, source.mapping_status
                FROM veltrix_ai_analyst.canonical_fixture_sources source
                JOIN veltrix_ai_analyst.canonical_fixtures canonical
                  ON canonical.id = source.canonical_fixture_id
                WHERE source.provider_fixture_row_id = %s
                """,
                (fixture["provider_fixture_row_id"],),
            )
            expected_home = canonical_team_ids[fixture["home_team_provider_id"]]
            expected_away = canonical_team_ids[fixture["away_team_provider_id"]]
            expected_identity = (
                "CONFLICT" if fixture["provider_fixture_id"] in conflict_ids
                else "IDENTITY_REVIEW_REQUIRED"
            )
            if existing:
                expected = (
                    fixture["kickoff_at"], fixture["status"], fixture["home_goals"],
                    fixture["away_goals"], canonical_competition_id, expected_home,
                    expected_away, expected_identity, "SOURCE_ROW_ONLY", scope.provider, scope.source_id,
                    fixture["provider_fixture_id"], fixture["source_observation_id"],
                    fixture["source_sighting_id"], fixture["provider_response_id"],
                    scope.rights_approval_id, fixture["payload_sha256"],
                    "EXACT_PROVIDER_FIXTURE_ID", "REVIEW_REQUIRED",
                )
                actual = (
                    existing["kickoff_at"], existing["status"], existing["home_goals"],
                    existing["away_goals"], existing["canonical_competition_id"],
                    existing["home_canonical_team_id"], existing["away_canonical_team_id"],
                    existing["identity_status"], existing["completeness_status"], existing["provider"], existing["source_id"],
                    existing["provider_fixture_id"], existing["source_observation_id"],
                    existing["source_sighting_id"], existing["provider_response_id"],
                    existing["rights_approval_id"], existing["payload_sha256"].strip(),
                    existing["mapping_method"], existing["mapping_status"],
                )
                if actual != expected:
                    raise CanonicalMaterializationError(
                        f"EXISTING_FIXTURE_MAPPING_DRIFT:{fixture['provider_fixture_id']}"
                    )
                reused_fixtures += 1
                continue

            canonical_fixture_id = connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.canonical_fixtures (
                    canonical_competition_id, home_canonical_team_id, away_canonical_team_id,
                    kickoff_at, status, home_goals, away_goals, identity_status,
                    completeness_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'SOURCE_ROW_ONLY')
                RETURNING id
                """,
                (
                    canonical_competition_id, expected_home, expected_away,
                    fixture["kickoff_at"], fixture["status"], fixture["home_goals"],
                    fixture["away_goals"], expected_identity,
                ),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.canonical_fixture_sources (
                    canonical_fixture_id, provider_fixture_row_id, provider, source_id,
                    provider_fixture_id, source_observation_id, source_sighting_id,
                    provider_response_id, rights_approval_id, payload_sha256,
                    mapping_method, mapping_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          'EXACT_PROVIDER_FIXTURE_ID', 'REVIEW_REQUIRED')
                """,
                (
                    canonical_fixture_id, fixture["provider_fixture_row_id"],
                    scope.provider, scope.source_id, fixture["provider_fixture_id"],
                    fixture["source_observation_id"], fixture["source_sighting_id"],
                    fixture["provider_response_id"], scope.rights_approval_id,
                    fixture["payload_sha256"],
                ),
            )
            created_fixtures += 1

    return {
        "mode": "APPLIED",
        "competition_created": competition_created,
        "teams_created": created_teams,
        "fixtures_created": created_fixtures,
        "fixtures_reused": reused_fixtures,
        "conflict_fixture_ids": list(plan.conflict_fixture_ids),
        "identity_reviews_created": 0,
        "pit_observations_promoted": 0,
        "provider_requests_made": 0,
        "plan": plan.as_dict(),
    }


def build_canonical_materialization_plan(
    connection: psycopg.Connection[Any],
    scope: CanonicalMaterializationScope,
) -> CanonicalMaterializationPlan:
    """Generic approved-source planner; historical function retained for compatibility."""
    return build_brazil_serie_b_materialization_plan(connection, scope)


def materialize_canonical_entities(
    connection: psycopg.Connection[Any],
    *,
    execute: bool = False,
    scope: CanonicalMaterializationScope,
) -> dict[str, Any]:
    """Generic approved-source materializer; dry-run remains the default."""
    return materialize_brazil_serie_b_canonical_entities(
        connection, execute=execute, scope=scope
    )
