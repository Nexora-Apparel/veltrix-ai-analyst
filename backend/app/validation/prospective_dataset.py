"""Leakage-safe expanding-window datasets from prospectively captured fixtures."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any


@dataclass(frozen=True, slots=True)
class FixtureIdentity:
    fixture_id: str
    provider: str
    source_id: str
    competition_id: str
    home_team_id: str
    away_team_id: str
    kickoff_at: datetime

    def __post_init__(self) -> None:
        for name in (
            "fixture_id", "provider", "source_id", "competition_id",
            "home_team_id", "away_team_id",
        ):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away team IDs must differ")
        _require_aware(self.kickoff_at, "kickoff_at")


@dataclass(frozen=True, slots=True)
class FixtureObservation:
    observation_id: int
    sighting_id: int
    provider_response_id: int
    fixture_id: str
    provider: str
    source_id: str
    retrieved_at: datetime
    observed_at: datetime
    availability_basis: str
    point_in_time_certifiable: bool
    payload_sha256: str
    raw_response_sha256: str
    payload: dict[str, Any]
    rights_approval_id: str | None = None
    rights_status: str | None = None
    rights_valid_from: datetime | None = None
    rights_valid_until: datetime | None = None
    rights_permitted_uses: tuple[str, ...] = ()
    rights_status_events: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        if min(self.observation_id, self.sighting_id, self.provider_response_id) < 1:
            raise ValueError("source observation, sighting and response IDs must be positive")
        if not self.fixture_id.strip() or not self.provider.strip() or not self.source_id.strip():
            raise ValueError("fixture and provider identity are required")
        _require_aware(self.retrieved_at, "retrieved_at")
        _require_aware(self.observed_at, "observed_at")
        if self.rights_valid_from is not None:
            _require_aware(self.rights_valid_from, "rights_valid_from")
        if self.rights_valid_until is not None:
            _require_aware(self.rights_valid_until, "rights_valid_until")
        if self.observed_at < self.retrieved_at:
            raise ValueError("system observation cannot precede retrieval")
        for digest in (self.payload_sha256, self.raw_response_sha256):
            if len(digest) != 64 or digest != digest.lower():
                raise ValueError("payload and raw response hashes must be lowercase SHA-256 digests")
            try:
                bytes.fromhex(digest)
            except ValueError:
                raise ValueError("payload and raw response hashes must be hexadecimal") from None


@dataclass(frozen=True, slots=True)
class ProspectiveDatasetRow:
    fixture_id: str
    provider: str
    source_id: str
    competition_id: str
    kickoff_at: datetime
    prediction_cutoff_at: datetime
    home_team_id: str
    away_team_id: str
    features: dict[str, float]
    feature_lineage: tuple[dict[str, Any], ...]
    label: dict[str, Any] | None
    label_observed_at: datetime | None
    label_observation_id: int | None
    label_lineage: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ExpandingFold:
    fold_number: int
    train_fixture_ids: tuple[str, ...]
    validation_fixture_ids: tuple[str, ...]
    train_cutoff_at: datetime
    validation_start_at: datetime
    validation_end_at: datetime


def _require_aware(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")


def _status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or "").strip().casefold()


def _score(payload: dict[str, Any], field: str) -> int | None:
    value = payload.get(field)
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None


def _validate_observation_fixture_identity(
    fixture: FixtureIdentity,
    observation: FixtureObservation,
) -> None:
    """Reject stale or cross-fixture observations rather than merging identities."""
    payload = observation.payload
    expected = {
        "competition_id": fixture.competition_id,
        "home_team_id": fixture.home_team_id,
        "away_team_id": fixture.away_team_id,
    }
    for field, value in expected.items():
        supplied = payload.get(field)
        if supplied is not None and str(supplied) != value:
            raise ValueError(f"observation {field} does not match fixture identity")
    kickoff = payload.get("kickoff_at")
    if kickoff is not None:
        if not isinstance(kickoff, str):
            raise ValueError("observation kickoff_at must be an ISO timestamp")
        try:
            observed_kickoff = datetime.fromisoformat(kickoff)
        except ValueError:
            raise ValueError("observation kickoff_at is invalid") from None
        _require_aware(observed_kickoff, "observation kickoff_at")
        if observed_kickoff != fixture.kickoff_at:
            raise ValueError("observation kickoff_at does not match fixture identity")
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        provider_record_id = provenance.get("provider_record_id")
        if provider_record_id is not None and str(provider_record_id) != fixture.fixture_id.split(":")[-1]:
            raise ValueError("observation provider fixture ID does not match fixture identity")


def _rights_valid(
    observation: FixtureObservation,
    cutoff: datetime,
    required_uses: tuple[str, ...] = (
        "FEATURE_ENGINEERING",
        "MODEL_TRAINING",
        "MODEL_VALIDATION",
    ),
) -> bool:
    if (
        observation.rights_approval_id is None
        or observation.rights_status != "APPROVED"
        or observation.rights_valid_from is None
        or observation.rights_valid_from > cutoff
        or (
            observation.rights_valid_until is not None
            and observation.rights_valid_until <= cutoff
        )
        or not set(required_uses).issubset(observation.rights_permitted_uses)
    ):
        return False
    effective_events = []
    for event in observation.rights_status_events:
        status = event.get("status")
        effective_at = event.get("effective_at")
        if isinstance(effective_at, str):
            try:
                effective_at = datetime.fromisoformat(effective_at)
            except ValueError:
                return False
        if isinstance(effective_at, datetime):
            if effective_at.utcoffset() is None:
                return False
            if effective_at <= cutoff:
                effective_events.append((effective_at, str(status)))
    if effective_events:
        latest = max(effective_events, key=lambda item: item[0])
        if latest[1] != "APPROVED":
            return False
    return True


def _lineage(row: FixtureObservation) -> dict[str, Any]:
    return {
        "fixture_id": row.fixture_id,
        "provider": row.provider,
        "source_id": row.source_id,
        "source_observation_id": row.observation_id,
        "source_sighting_id": row.sighting_id,
        "provider_response_id": row.provider_response_id,
        "payload_sha256": row.payload_sha256,
        "raw_response_sha256": row.raw_response_sha256,
        "rights_approval_id": row.rights_approval_id,
        "rights_status": row.rights_status,
        "rights_valid_from": (
            row.rights_valid_from.isoformat() if row.rights_valid_from else None
        ),
        "rights_valid_until": (
            row.rights_valid_until.isoformat() if row.rights_valid_until else None
        ),
        "rights_permitted_uses": list(row.rights_permitted_uses),
        "rights_status_events": [
            {
                "status": event.get("status"),
                "effective_at": (
                    event["effective_at"].isoformat()
                    if isinstance(event.get("effective_at"), datetime)
                    else event.get("effective_at")
                ),
            }
            for event in row.rights_status_events
        ],
        "availability_basis": row.availability_basis,
        "point_in_time_certifiable": row.point_in_time_certifiable,
        "retrieved_at": row.retrieved_at.isoformat(),
        "system_observed_at": row.observed_at.isoformat(),
    }


def _finished_result(row: FixtureObservation) -> tuple[int, int] | None:
    if (
        row.availability_basis != "SYSTEM_OBSERVED_AT"
        or not row.point_in_time_certifiable
        or _status(row.payload) != "finished"
    ):
        return None
    home_goals = _score(row.payload, "home_goals")
    away_goals = _score(row.payload, "away_goals")
    if home_goals is None or away_goals is None:
        return None
    return home_goals, away_goals


def _optional_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _team_form(
    target_team_id: str,
    matches: list[tuple[FixtureIdentity, FixtureObservation, int, int]],
    target_kickoff: datetime,
    prefix: str,
    limit: int = 5,
) -> tuple[dict[str, float], list[FixtureObservation]]:
    appearances = [
        item for item in matches
        if item[0].home_team_id == target_team_id or item[0].away_team_id == target_team_id
    ]
    appearances.sort(key=lambda item: (item[0].kickoff_at, item[1].observed_at), reverse=True)
    selected = appearances[:limit]
    points: list[float] = []
    goals_for: list[float] = []
    goals_against: list[float] = []
    statistic_values: dict[str, list[float]] = defaultdict(list)
    late_goals_for: list[float] = []
    late_goals_against: list[float] = []
    substitutions: list[float] = []
    stats_coverage = 0
    events_coverage = 0
    statistic_keys = (
        "shots_on_target",
        "shots_off_target",
        "dangerous_attacks",
        "attacks",
        "possession",
    )
    for fixture, observation, home_goals, away_goals in selected:
        side = "home" if fixture.home_team_id == target_team_id else "away"
        opponent_side = "away" if side == "home" else "home"
        if side == "home":
            scored, conceded = home_goals, away_goals
        else:
            scored, conceded = away_goals, home_goals
        goals_for.append(float(scored))
        goals_against.append(float(conceded))
        points.append(3.0 if scored > conceded else 1.0 if scored == conceded else 0.0)

        payload = observation.payload
        statistics = payload.get("statistics")
        has_statistics = False
        if isinstance(statistics, dict):
            for key in statistic_keys:
                pair = statistics.get(key)
                value = _optional_number(pair.get(side)) if isinstance(pair, dict) else None
                if value is not None:
                    statistic_values[key].append(value)
                    has_statistics = True
            first_half = statistics.get("first_half")
            if isinstance(first_half, dict):
                for key in ("shots_on_target", "dangerous_attacks"):
                    pair = first_half.get(key)
                    value = _optional_number(pair.get(side)) if isinstance(pair, dict) else None
                    if value is not None:
                        statistic_values[f"first_half_{key}"].append(value)
                        has_statistics = True
        for key, payload_key in (
            ("corners", f"{side}_corners"),
            ("yellow_cards", f"{side}_yellow_cards"),
            ("red_cards", f"{side}_red_cards"),
        ):
            value = _optional_number(payload.get(payload_key))
            if value is not None:
                statistic_values[key].append(value)
                has_statistics = True
        if has_statistics:
            stats_coverage += 1

        raw_events = payload.get("events")
        if isinstance(raw_events, list):
            events_coverage += 1
            late_for = 0.0
            late_against = 0.0
            substitution_count = 0.0
            for event in raw_events:
                if not isinstance(event, dict):
                    continue
                event_type = str(event.get("type") or "").casefold()
                event_team = str(event.get("team") or "").casefold()
                minute = _optional_number(event.get("minute"))
                if event_type == "goal" and minute is not None and minute >= 76:
                    if event_team == side:
                        late_for += 1.0
                    elif event_team == opponent_side:
                        late_against += 1.0
                elif event_type == "substitution" and event_team == side:
                    substitution_count += 1.0
            late_goals_for.append(late_for)
            late_goals_against.append(late_against)
            substitutions.append(substitution_count)
    latest_kickoff = selected[0][0].kickoff_at if selected else None
    rest_days = (
        max(0.0, (target_kickoff - latest_kickoff).total_seconds() / 86400.0)
        if latest_kickoff is not None else 0.0
    )
    values = {
        f"{prefix}_matches_last5": float(len(selected)),
        f"{prefix}_points_per_match_last5": mean(points) if points else 0.0,
        f"{prefix}_goals_for_per_match_last5": mean(goals_for) if goals_for else 0.0,
        f"{prefix}_goals_against_per_match_last5": mean(goals_against) if goals_against else 0.0,
        f"{prefix}_goal_difference_per_match_last5": (
            mean(goals_for) - mean(goals_against) if selected else 0.0
        ),
        f"{prefix}_rest_days": rest_days,
        f"{prefix}_stats_coverage_last5": float(stats_coverage),
        f"{prefix}_events_coverage_last5": float(events_coverage),
    }
    for key, metric_values in statistic_values.items():
        if metric_values:
            values[f"{prefix}_{key}_avg_last5"] = mean(metric_values)
    if late_goals_for:
        values[f"{prefix}_late_goals_for_avg_last5"] = mean(late_goals_for)
        values[f"{prefix}_late_goals_against_avg_last5"] = mean(late_goals_against)
        values[f"{prefix}_substitutions_avg_last5"] = mean(substitutions)
    return values, [item[1] for item in selected]


def build_prospective_dataset(
    fixtures: list[FixtureIdentity] | tuple[FixtureIdentity, ...],
    observations: list[FixtureObservation] | tuple[FixtureObservation, ...],
) -> tuple[ProspectiveDatasetRow, ...]:
    """Build one target row per fixture with a genuine pre-kickoff snapshot.

    A schedule observation supplies the target prediction cutoff. Every feature
    source result must have been captured no later than that cutoff and belong
    to an earlier fixture in the same competition. Labels are read only from a
    finished observation captured after that target fixture's kickoff.
    """
    fixture_by_id = {fixture.fixture_id: fixture for fixture in fixtures}
    if len(fixture_by_id) != len(fixtures):
        raise ValueError("duplicate provider fixture IDs")
    grouped: dict[str, list[FixtureObservation]] = defaultdict(list)
    for observation in observations:
        fixture = fixture_by_id.get(observation.fixture_id)
        if fixture is None:
            continue
        if (observation.provider, observation.source_id) != (fixture.provider, fixture.source_id):
            raise ValueError("observation provider identity does not match fixture")
        _validate_observation_fixture_identity(fixture, observation)
        grouped[observation.fixture_id].append(observation)

    finished_matches_by_competition: dict[
        tuple[str, str, str], list[tuple[FixtureIdentity, FixtureObservation, int, int]]
    ] = defaultdict(list)
    for fixture in fixtures:
        for observation in grouped.get(fixture.fixture_id, []):
            result = _finished_result(observation)
            if result is not None and observation.observed_at > fixture.kickoff_at:
                finished_matches_by_competition[
                    (fixture.provider, fixture.source_id, fixture.competition_id)
                ].append((fixture, observation, result[0], result[1]))

    rows: list[ProspectiveDatasetRow] = []
    for fixture in sorted(fixtures, key=lambda item: (item.kickoff_at, item.fixture_id)):
        fixture_observations = grouped.get(fixture.fixture_id, [])
        pre_match_snapshots = [
            row for row in fixture_observations
            if row.availability_basis == "SYSTEM_OBSERVED_AT"
            and row.point_in_time_certifiable
            and _status(row.payload) == "scheduled"
            and row.observed_at < fixture.kickoff_at
            and _rights_valid(row, row.observed_at)
        ]
        if not pre_match_snapshots:
            continue
        snapshot = max(pre_match_snapshots, key=lambda row: (row.observed_at, row.sighting_id))
        cutoff = snapshot.observed_at
        competition_matches = finished_matches_by_competition[
            (fixture.provider, fixture.source_id, fixture.competition_id)
        ]
        eligible_by_fixture: dict[str, tuple[FixtureIdentity, FixtureObservation, int, int]] = {}
        for item in competition_matches:
            source_fixture, source_observation, _, _ = item
            if (
                source_fixture.fixture_id == fixture.fixture_id
                or source_fixture.kickoff_at >= fixture.kickoff_at
                or source_observation.observed_at > cutoff
                or not _rights_valid(source_observation, cutoff)
            ):
                continue
            previous = eligible_by_fixture.get(source_fixture.fixture_id)
            if previous is None or source_observation.observed_at > previous[1].observed_at:
                eligible_by_fixture[source_fixture.fixture_id] = item
        eligible_matches = list(eligible_by_fixture.values())
        home_features, home_lineage = _team_form(
            fixture.home_team_id, eligible_matches, fixture.kickoff_at, "home"
        )
        away_features, away_lineage = _team_form(
            fixture.away_team_id, eligible_matches, fixture.kickoff_at, "away"
        )
        recent_competition = sorted(
            eligible_matches,
            key=lambda item: (item[0].kickoff_at, item[1].observed_at),
            reverse=True,
        )[:20]
        totals = [float(home + away) for _, _, home, away in recent_competition]
        btts_values = [float(home > 0 and away > 0) for _, _, home, away in recent_competition]
        over_values = [float(home + away > 2) for _, _, home, away in recent_competition]
        features = {
            **home_features,
            **away_features,
            "competition_matches_last20": float(len(recent_competition)),
            "competition_goals_per_match_last20": mean(totals) if totals else 0.0,
            "competition_btts_rate_last20": mean(btts_values) if btts_values else 0.0,
            "competition_over25_rate_last20": mean(over_values) if over_values else 0.0,
        }
        lineage_by_id = {
            (item.observation_id, item.sighting_id): item
            for item in [snapshot, *home_lineage, *away_lineage, *(match[1] for match in recent_competition)]
        }
        lineage = tuple(
            _lineage(item)
            for item in sorted(
                lineage_by_id.values(),
                key=lambda item: (item.observed_at, item.observation_id, item.sighting_id),
            )
        )
        labels = [
            row for row in fixture_observations
            if _finished_result(row) is not None and row.observed_at > fixture.kickoff_at
        ]
        label_observation = max(
            labels, key=lambda row: (row.observed_at, row.sighting_id), default=None
        )
        label = None
        label_observed_at = None
        label_observation_id = None
        label_lineage = None
        if label_observation is not None:
            home_goals, away_goals = _finished_result(label_observation) or (0, 0)
            label = {
                "home_goals": home_goals,
                "away_goals": away_goals,
                "home_win": home_goals > away_goals,
                "draw": home_goals == away_goals,
                "away_win": home_goals < away_goals,
                "btts": home_goals > 0 and away_goals > 0,
                "over_25": home_goals + away_goals > 2,
            }
            label_observed_at = label_observation.observed_at
            label_observation_id = label_observation.observation_id
            label_lineage = _lineage(label_observation)
        rows.append(
            ProspectiveDatasetRow(
                fixture_id=fixture.fixture_id,
                provider=fixture.provider,
                source_id=fixture.source_id,
                competition_id=fixture.competition_id,
                kickoff_at=fixture.kickoff_at,
                prediction_cutoff_at=cutoff,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                features=features,
                feature_lineage=lineage,
                label=label,
                label_observed_at=label_observed_at,
                label_observation_id=label_observation_id,
                label_lineage=label_lineage,
            )
        )
    return tuple(rows)


def build_expanding_window_folds(
    rows: tuple[ProspectiveDatasetRow, ...] | list[ProspectiveDatasetRow],
    *,
    minimum_training_fixtures: int = 30,
    validation_block_fixtures: int = 25,
) -> tuple[ExpandingFold, ...]:
    """Create chronological folds with simultaneous kickoffs kept together.

    Training labels must themselves have been observed before the first
    validation kickoff. The validation block is selected by chronological
    fixture order; no random split or post-kickoff feature is permitted.
    """
    if minimum_training_fixtures < 1 or validation_block_fixtures < 1:
        raise ValueError("fold sizes must be positive")
    labelled = [row for row in rows if row.label is not None and row.label_observed_at is not None]
    labelled.sort(key=lambda row: (row.kickoff_at, row.fixture_id))
    groups: list[list[ProspectiveDatasetRow]] = []
    for row in labelled:
        if not groups or groups[-1][0].kickoff_at != row.kickoff_at:
            groups.append([row])
        else:
            groups[-1].append(row)

    folds: list[ExpandingFold] = []
    train_groups: list[list[ProspectiveDatasetRow]] = []
    group_index = 0
    fold_number = 1
    while group_index < len(groups):
        train_rows = [row for group in train_groups for row in group]
        if len(train_rows) >= minimum_training_fixtures:
            validation_groups: list[list[ProspectiveDatasetRow]] = []
            validation_count = 0
            cursor = group_index
            while cursor < len(groups) and validation_count < validation_block_fixtures:
                validation_groups.append(groups[cursor])
                validation_count += len(groups[cursor])
                cursor += 1
            validation_rows = [row for group in validation_groups for row in group]
            validation_start = validation_rows[0].kickoff_at
            validation_end = validation_rows[-1].kickoff_at
            eligible_train = [
                row for row in train_rows
                if row.kickoff_at < validation_start
                and row.label_observed_at is not None
                and row.label_observed_at < validation_start
            ]
            if len(eligible_train) >= minimum_training_fixtures and validation_rows:
                folds.append(
                    ExpandingFold(
                        fold_number=fold_number,
                        train_fixture_ids=tuple(row.fixture_id for row in eligible_train),
                        validation_fixture_ids=tuple(row.fixture_id for row in validation_rows),
                        train_cutoff_at=max(
                            row.label_observed_at
                            for row in eligible_train
                            if row.label_observed_at is not None
                        ),
                        validation_start_at=validation_start,
                        validation_end_at=validation_end,
                    )
                )
                fold_number += 1
            train_groups.extend(validation_groups)
            group_index = cursor
        else:
            train_groups.append(groups[group_index])
            group_index += 1
    return tuple(folds)
