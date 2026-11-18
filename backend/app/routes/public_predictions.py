"""Minimal read API for published V1 predictions only."""
from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import psycopg
from fastapi import APIRouter, HTTPException, status
from psycopg.rows import dict_row

from app.contracts.public_prediction import (
    PublicFixture,
    PublicPrediction,
    PublicPredictionList,
    PublicPredictionMarkets,
)

router = APIRouter(prefix="/v1/predictions", tags=["predictions"])
DATABASE_NAME = "veltrix_ai_analyst"

_MARKET_NAMES = {
    "1X2": "one_x_two",
    "BTTS": "btts",
    "TOTALS_1_5": "over_under_1_5",
    "TOTALS_2_5": "over_under_2_5",
    "TOTALS_3_5": "over_under_3_5",
}


def _database_connection():
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PREDICTIONS_UNAVAILABLE",
        )
    try:
        connection = psycopg.connect(dsn, row_factory=dict_row)
    except psycopg.Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PREDICTIONS_UNAVAILABLE",
        ) from None
    if connection.info.dbname != DATABASE_NAME:
        connection.close()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PREDICTIONS_UNAVAILABLE",
        )
    return connection


def _public_prediction(
    fixture_row: dict[str, Any],
    market_rows: Iterable[dict[str, Any]],
) -> PublicPrediction:
    markets: dict[str, dict[str, float]] = {}
    for row in market_rows:
        public_name = _MARKET_NAMES.get(row["market"])
        if public_name is None:
            raise ValueError("UNSUPPORTED_PUBLIC_MARKET")
        markets.setdefault(public_name, {})[row["outcome"]] = float(row["probability"])

    return PublicPrediction(
        prediction_id=fixture_row["prediction_id"],
        fixture=PublicFixture(
            fixture_id=fixture_row["canonical_fixture_id"],
            competition=fixture_row["competition"],
            home_team=fixture_row["home_team"],
            away_team=fixture_row["away_team"],
            kickoff_at=fixture_row["kickoff_at"],
        ),
        markets=PublicPredictionMarkets(**markets),
        expected_home_goals=fixture_row["expected_home_goals"],
        expected_away_goals=fixture_row["expected_away_goals"],
    )


_FIXTURE_QUERY = """
    SELECT
        published.prediction_id,
        published.canonical_fixture_id,
        competition.display_name AS competition,
        home_team.display_name AS home_team,
        away_team.display_name AS away_team,
        fixture.kickoff_at,
        published.expected_home_goals,
        published.expected_away_goals
    FROM veltrix_ai_analyst.published_predictions published
    JOIN veltrix_ai_analyst.canonical_fixtures fixture
      ON fixture.id = published.canonical_fixture_id
    JOIN veltrix_ai_analyst.canonical_competitions competition
      ON competition.id = fixture.canonical_competition_id
    JOIN veltrix_ai_analyst.canonical_teams home_team
      ON home_team.id = fixture.home_canonical_team_id
    JOIN veltrix_ai_analyst.canonical_teams away_team
      ON away_team.id = fixture.away_canonical_team_id
"""


def _load_public_predictions(*, prediction_id: UUID | None = None) -> tuple[PublicPrediction, ...]:
    connection = _database_connection()
    try:
        with connection:
            if prediction_id is None:
                fixtures = connection.execute(
                    _FIXTURE_QUERY + """
                    WHERE fixture.kickoff_at > %s
                    ORDER BY fixture.kickoff_at, published.prediction_id
                    LIMIT 100
                    """,
                    (datetime.now(UTC),),
                ).fetchall()
            else:
                fixtures = connection.execute(
                    _FIXTURE_QUERY + """
                    WHERE published.prediction_id = %s
                      AND fixture.kickoff_at > %s
                    """,
                    (prediction_id, datetime.now(UTC)),
                ).fetchall()

            if not fixtures:
                return ()

            prediction_ids = [row["prediction_id"] for row in fixtures]
            market_rows = connection.execute(
                """
                SELECT prediction_id, market, outcome, probability
                FROM veltrix_ai_analyst.published_prediction_markets
                WHERE prediction_id = ANY(%s)
                ORDER BY prediction_id, market, outcome
                """,
                (prediction_ids,),
            ).fetchall()
            grouped: dict[UUID, list[dict[str, Any]]] = {}
            for row in market_rows:
                grouped.setdefault(row["prediction_id"], []).append(row)

            return tuple(
                _public_prediction(row, grouped.get(row["prediction_id"], []))
                for row in fixtures
            )
    except (psycopg.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PREDICTIONS_UNAVAILABLE",
        ) from None
    finally:
        connection.close()


@router.get("", response_model=PublicPredictionList)
def list_predictions() -> PublicPredictionList:
    """Return upcoming published predictions with market probabilities only."""
    return PublicPredictionList(predictions=_load_public_predictions())


@router.get("/{prediction_id}", response_model=PublicPrediction)
def get_prediction(prediction_id: UUID) -> PublicPrediction:
    """Return one upcoming published prediction; unpublished IDs are not exposed."""
    predictions = _load_public_predictions(prediction_id=prediction_id)
    if not predictions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PREDICTION_NOT_FOUND",
        )
    return predictions[0]
