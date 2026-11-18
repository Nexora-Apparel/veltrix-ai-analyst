"""Fail-closed normalization for 5Dollar scheduled fixture catalogue responses."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

class FixtureCatalogueError(ValueError):
    """The 5Dollar fixture catalogue response is malformed or inconsistent."""


def _parse_aware(value: object, field_name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise FixtureCatalogueError(f"{field_name}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise FixtureCatalogueError(f"{field_name}_INVALID") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise FixtureCatalogueError(f"{field_name}_MUST_BE_TIMEZONE_AWARE")
    return parsed.astimezone(UTC)


def normalize_scheduled_fixture_catalogue(
    payload: Any, *, competition_id: str, as_of: datetime
) -> tuple[tuple[dict[str, str], ...], bool, int]:
    """Normalize only future scheduled fixtures and preserve pagination completeness."""
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise FixtureCatalogueError("AS_OF_MUST_BE_TIMEZONE_AWARE")
    if not isinstance(payload, dict) or payload.get("success") != 1:
        raise FixtureCatalogueError("FIXTURE_RESPONSE_UNSUCCESSFUL")
    rows = payload.get("data")
    pagination = payload.get("pagination")
    if not isinstance(rows, list):
        raise FixtureCatalogueError("FIXTURE_DATA_MUST_BE_ARRAY")
    if not isinstance(pagination, dict) or not isinstance(
        pagination.get("has_more"), bool
    ):
        raise FixtureCatalogueError("FIXTURE_PAGINATION_METADATA_REQUIRED")

    fixtures: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    excluded_nonfuture = 0
    for row in rows:
        if not isinstance(row, dict):
            raise FixtureCatalogueError("FIXTURE_ROW_MUST_BE_OBJECT")
        fixture_id = row.get("id")
        status = row.get("status")
        league = row.get("league")
        teams = row.get("teams")
        if not isinstance(fixture_id, (str, int)) or str(fixture_id).strip() == "":
            raise FixtureCatalogueError("FIXTURE_ID_REQUIRED")
        fixture_id = str(fixture_id)
        if fixture_id in seen_ids:
            raise FixtureCatalogueError("DUPLICATE_FIXTURE_ID")
        if status != "scheduled":
            raise FixtureCatalogueError("UNEXPECTED_FIXTURE_STATUS")
        if not isinstance(league, dict) or str(league.get("id")) != competition_id:
            raise FixtureCatalogueError("FIXTURE_COMPETITION_MISMATCH")
        if not isinstance(teams, dict):
            raise FixtureCatalogueError("FIXTURE_TEAMS_REQUIRED")
        home = teams.get("home")
        away = teams.get("away")
        if not isinstance(home, dict) or not isinstance(away, dict):
            raise FixtureCatalogueError("FIXTURE_HOME_AWAY_REQUIRED")
        home_name = home.get("name")
        away_name = away.get("name")
        if not all(
            isinstance(name, str) and name.strip()
            for name in (home_name, away_name)
        ):
            raise FixtureCatalogueError("FIXTURE_TEAM_NAME_REQUIRED")
        kickoff = _parse_aware(row.get("kickoff_utc"), "FIXTURE_KICKOFF")
        seen_ids.add(fixture_id)
        if kickoff <= as_of.astimezone(UTC):
            excluded_nonfuture += 1
            continue
        fixtures.append(
            {
                "provider_fixture_id": fixture_id,
                "competition_id": competition_id,
                "home_team": home_name.strip(),
                "away_team": away_name.strip(),
                "kickoff_at": kickoff.isoformat(),
            }
        )

    fixtures.sort(key=lambda item: (item["kickoff_at"], item["provider_fixture_id"]))
    return tuple(fixtures), pagination["has_more"], excluded_nonfuture
