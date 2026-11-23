"""Read-only API for explicitly isolated research shadow forecasts."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import psycopg
from fastapi import APIRouter, HTTPException, status

from app.wat_calendar import wat_day_window_utc

from app.routes.public_predictions import (
    _database_connection,
    _public_prediction,
)

router = APIRouter(prefix="/v1/research/predictions", tags=["research-predictions"])
MODEL_VERSION = "hierarchical-poisson-newton-shadow-v2"
_ADMISSION_PATH = (
    Path(__file__).resolve().parents[1]
    / "research" / "admissions" / f"{MODEL_VERSION}.json"
)


def _model_admitted() -> bool:
    try:
        record = json.loads(_ADMISSION_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        record.get("model_version") == MODEL_VERSION
        and record.get("tier") == "SHADOW"
        and record.get("certification") == "RETROSPECTIVE_NOT_PIT_CERTIFIED"
        and record.get("production_promotion") == "LOCKED"
        and record.get("value_betting") == "LOCKED"
        and record.get("app_display_enabled") is False
        and all(
            isinstance(record.get(field), str)
            and len(record[field]) == 64
            and all(char in "0123456789abcdef" for char in record[field])
            for field in ("config_sha256", "training_data_sha256", "report_sha256")
        )
    )


def _quarantined_response() -> dict[str, Any]:
    return {
        "status": "MODEL_QUARANTINED",
        "research_only": True,
        "research_label": "RESEARCH ONLY",
        "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
        "publication_status": "NOT_PUBLISHED",
        "production_promotion": "LOCKED",
        "value_betting": "LOCKED",
        "generated_at": None,
        "training_fixture_count": 0,
        "model_version": None,
        "predictions": [],
    }

_RESEARCH_QUERY = """
    WITH latest_run AS (
        SELECT run_key, generated_at, status, training_fixture_count, model_version, report
        FROM veltrix_ai_analyst.research_shadow_forecast_runs
        WHERE model_version = %s
        ORDER BY generated_at DESC, created_at DESC
        LIMIT 1
    )
    SELECT
        latest_run.run_key,
        latest_run.generated_at,
        latest_run.training_fixture_count,
        latest_run.model_version,
        forecast.value AS forecast,
        fixture.id AS canonical_fixture_id,
        competition.display_name AS competition,
        home_team.display_name AS home_team,
        away_team.display_name AS away_team,
        fixture.kickoff_at
    FROM latest_run
    CROSS JOIN LATERAL jsonb_array_elements(latest_run.report->'predictions')
        AS forecast(value)
    JOIN veltrix_ai_analyst.canonical_fixtures fixture
      ON fixture.id = (forecast.value->>'canonical_fixture_id')::UUID
    JOIN veltrix_ai_analyst.canonical_competitions competition
      ON competition.id = fixture.canonical_competition_id
    JOIN veltrix_ai_analyst.canonical_teams home_team
      ON home_team.id = fixture.home_canonical_team_id
    JOIN veltrix_ai_analyst.canonical_teams away_team
      ON away_team.id = fixture.away_canonical_team_id
    WHERE latest_run.status = 'SHADOW_FORECASTS_READY'
      AND latest_run.report->>'research_only' = 'true'
      AND latest_run.report->>'production_promotion' = 'LOCKED'
      AND latest_run.report->>'value_betting' = 'LOCKED'
      AND latest_run.report->>'release_eligible' = 'false'
      AND latest_run.generated_at > NOW() - INTERVAL '36 hours'
      AND fixture.kickoff_at >= %s
      AND fixture.kickoff_at < %s
      AND forecast.value->>'publication_status' = 'NOT_PUBLISHED'
      AND forecast.value->>'value_betting_status' = 'LOCKED'
    ORDER BY fixture.kickoff_at, fixture.id
    LIMIT 25
"""


def _research_prediction(row: dict[str, Any]) -> dict[str, Any]:
    forecast = row["forecast"]
    markets = forecast["markets"]
    market_rows = [
        {"market": market, "outcome": outcome, "probability": probability}
        for market, outcomes in markets.items()
        for outcome, probability in outcomes.items()
    ]
    fixture_row = {
        "prediction_id": uuid5(
            NAMESPACE_URL,
            f"veltrix-shadow:{row['run_key']}:{row['canonical_fixture_id']}",
        ),
        "canonical_fixture_id": row["canonical_fixture_id"],
        "competition": row["competition"],
        "home_team": row["home_team"],
        "away_team": row["away_team"],
        "kickoff_at": row["kickoff_at"],
        "expected_home_goals": forecast.get("expected_home_goals"),
        "expected_away_goals": forecast.get("expected_away_goals"),
    }
    prediction = _public_prediction(fixture_row, market_rows)
    return prediction.model_dump(mode="json")


@router.get("")
def list_research_predictions() -> dict[str, Any]:
    """Return today's WAT shadow forecasts without exposing them as published predictions."""
    # The code admission record is necessary but not sufficient: an owner must
    # separately enable research display after reviewing the first live run.
    if (
        os.getenv("VELTRIX_RESEARCH_SHADOW_DISPLAY_ENABLED") != "true"
        or not _model_admitted()
    ):
        return _quarantined_response()

    connection = _database_connection()
    try:
        with connection:
            day_start_utc, day_end_utc = wat_day_window_utc()
            rows = connection.execute(
                _RESEARCH_QUERY, (MODEL_VERSION, day_start_utc, day_end_utc)
            ).fetchall()
        if not rows:
            return {
                "status": "NO_RESEARCH_FORECASTS_AVAILABLE",
                "research_only": True,
                "research_label": "RESEARCH ONLY",
                "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
                "publication_status": "NOT_PUBLISHED",
                "production_promotion": "LOCKED",
                "value_betting": "LOCKED",
                "generated_at": None,
                "training_fixture_count": 0,
                "model_version": None,
                "predictions": [],
            }
        first = rows[0]
        return {
            "status": "SHADOW_FORECASTS_READY",
            "research_only": True,
            "research_label": "RESEARCH ONLY",
            "certification": "RETROSPECTIVE_NOT_PIT_CERTIFIED",
            "publication_status": "NOT_PUBLISHED",
            "production_promotion": "LOCKED",
            "value_betting": "LOCKED",
            "generated_at": first["generated_at"].isoformat(),
            "training_fixture_count": first["training_fixture_count"],
            "model_version": first["model_version"],
            "predictions": [_research_prediction(row) for row in rows],
        }
    except (psycopg.Error, KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RESEARCH_PREDICTIONS_UNAVAILABLE",
        ) from None
    finally:
        connection.close()
