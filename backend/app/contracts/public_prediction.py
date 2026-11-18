"""Minimal client-facing prediction contract.

Internal model diagnostics, system notes and research reports are deliberately
excluded from the public prediction payload.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from app.contracts.prediction import ContractModel


class PublicFixture(ContractModel):
    fixture_id: UUID
    competition: str = Field(min_length=1, max_length=160)
    home_team: str = Field(min_length=1, max_length=160)
    away_team: str = Field(min_length=1, max_length=160)
    kickoff_at: datetime

    @model_validator(mode="after")
    def validate_fixture(self) -> PublicFixture:
        if self.home_team == self.away_team:
            raise ValueError("home and away team names must differ")
        if self.kickoff_at.tzinfo is None or self.kickoff_at.utcoffset() is None:
            raise ValueError("kickoff_at must be timezone-aware")
        return self


class PublicPredictionMarkets(ContractModel):
    one_x_two: dict[Literal["HOME", "DRAW", "AWAY"], float]
    btts: dict[Literal["YES", "NO"], float]
    over_under_1_5: dict[Literal["OVER", "UNDER"], float]
    over_under_2_5: dict[Literal["OVER", "UNDER"], float]
    over_under_3_5: dict[Literal["OVER", "UNDER"], float]

    @field_validator(
        "one_x_two", "btts", "over_under_1_5", "over_under_2_5", "over_under_3_5"
    )
    @classmethod
    def validate_market_distribution(cls, values: dict[str, float]) -> dict[str, float]:
        if not values or any(not 0.0 <= probability <= 1.0 for probability in values.values()):
            raise ValueError("market probabilities must be in [0, 1]")
        if abs(sum(values.values()) - 1.0) > 1e-8:
            raise ValueError("market probabilities must sum to one")
        return values


class PublicPrediction(ContractModel):
    prediction_id: UUID
    fixture: PublicFixture
    markets: PublicPredictionMarkets
    expected_home_goals: float | None = Field(default=None, ge=0)
    expected_away_goals: float | None = Field(default=None, ge=0)


class PublicPredictionList(ContractModel):
    predictions: tuple[PublicPrediction, ...]
