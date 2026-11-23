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

from app.wat_calendar import wat_day_window_utc

from app.contracts.public_prediction import (
    PublicFinalScore,
    PublicFixture,
    PublicPrediction,
    PublicPredictionHistoryItem,
    PublicPredictionHistoryList,
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
                    WHERE fixture.kickoff_at >= %s
                      AND fixture.kickoff_at < %s
                    ORDER BY fixture.kickoff_at, published.prediction_id
                    LIMIT 100
                    """,
                    wat_day_window_utc(),
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
    """Return published predictions for the complete WAT calendar day."""
    return PublicPredictionList(predictions=_load_public_predictions())


@router.get("/history", response_model=PublicPredictionHistoryList)
def list_prediction_history() -> PublicPredictionHistoryList:
    """Return previously published fixtures with evidence-backed final scores."""
    return PublicPredictionHistoryList(predictions=_load_prediction_history())


_HISTORY_QUERY = """
    SELECT
        published.prediction_id,
        published.canonical_fixture_id,
        competition.display_name AS competition,
        home_team.display_name AS home_team,
        away_team.display_name AS away_team,
        fixture.kickoff_at,
        published.expected_home_goals,
        published.expected_away_goals,
        published.generated_at,
        first_publication.published_at,
        latest_publication.decision AS publication_status,
        settlement.home_goals AS settled_home_goals,
        settlement.away_goals AS settled_away_goals,
        settlement.settled_at
    FROM veltrix_ai_analyst.predictions published
    JOIN veltrix_ai_analyst.canonical_fixtures fixture
      ON fixture.id = published.canonical_fixture_id
    JOIN veltrix_ai_analyst.canonical_competitions competition
      ON competition.id = fixture.canonical_competition_id
    JOIN veltrix_ai_analyst.canonical_teams home_team
      ON home_team.id = fixture.home_canonical_team_id
    JOIN veltrix_ai_analyst.canonical_teams away_team
      ON away_team.id = fixture.away_canonical_team_id
    JOIN LATERAL (
        SELECT MIN(event.effective_at) AS published_at
        FROM veltrix_ai_analyst.prediction_publication_events event
        WHERE event.prediction_id = published.prediction_id
          AND event.decision = 'PUBLISHED'
    ) first_publication ON first_publication.published_at IS NOT NULL
    JOIN LATERAL (
        SELECT event.decision
        FROM veltrix_ai_analyst.prediction_publication_events event
        WHERE event.prediction_id = published.prediction_id
        ORDER BY event.effective_at DESC, event.id DESC
        LIMIT 1
    ) latest_publication ON TRUE
    LEFT JOIN veltrix_ai_analyst.latest_prediction_settlements settlement
      ON settlement.prediction_id = published.prediction_id
    WHERE fixture.kickoff_at <= %s
      AND first_publication.published_at < fixture.kickoff_at
    ORDER BY fixture.kickoff_at DESC, published.generated_at DESC,
             published.prediction_id
    LIMIT 250
"""


def _public_prediction_history_item(
    fixture_row: dict[str, Any],
    market_rows: Iterable[dict[str, Any]],
) -> PublicPredictionHistoryItem:
    base = _public_prediction(fixture_row, market_rows)
    settled_at = fixture_row["settled_at"]
    final_score = (
        PublicFinalScore(
            home_goals=fixture_row["settled_home_goals"],
            away_goals=fixture_row["settled_away_goals"],
        )
        if settled_at is not None
        else None
    )
    return PublicPredictionHistoryItem(
        **base.model_dump(),
        generated_at=fixture_row["generated_at"],
        published_at=fixture_row["published_at"],
        publication_status=fixture_row["publication_status"],
        settlement_status="SETTLED" if settled_at is not None else "PENDING_RESULT",
        final_score=final_score,
        settled_at=settled_at,
    )


def _load_prediction_history() -> tuple[PublicPredictionHistoryItem, ...]:
    connection = _database_connection()
    try:
        with connection:
            fixtures = connection.execute(
                _HISTORY_QUERY,
                (datetime.now(UTC),),
            ).fetchall()
            if not fixtures:
                return ()

            prediction_ids = [row["prediction_id"] for row in fixtures]
            market_rows = connection.execute(
                """
                SELECT prediction_id, market, outcome, probability
                FROM veltrix_ai_analyst.prediction_market_probabilities
                WHERE prediction_id = ANY(%s)
                ORDER BY prediction_id, market, outcome
                """,
                (prediction_ids,),
            ).fetchall()
            grouped: dict[UUID, list[dict[str, Any]]] = {}
            for row in market_rows:
                grouped.setdefault(row["prediction_id"], []).append(row)

            return tuple(
                _public_prediction_history_item(
                    row, grouped.get(row["prediction_id"], [])
                )
                for row in fixtures
            )
    except (psycopg.Error, ValueError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PREDICTION_HISTORY_UNAVAILABLE",
        ) from None
    finally:
        connection.close()


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
