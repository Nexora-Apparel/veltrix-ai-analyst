from __future__ import annotations

import pytest

from app.validation.temperature_scaling import apply_temperature, fit_temperature


def test_temperature_scaling_preserves_probability_simplex():
    rows = [(0.7, 0.2, 0.1), (0.1, 0.3, 0.6)]
    scaled = apply_temperature(rows, 1.7)
    assert all(sum(row) == pytest.approx(1.0) for row in scaled)
    assert all(all(0.0 <= value <= 1.0 for value in row) for row in scaled)


def test_temperature_one_is_identity_within_numeric_tolerance():
    rows = [(0.7, 0.2, 0.1), (0.1, 0.3, 0.6)]
    scaled = apply_temperature(rows, 1.0)
    for actual, expected in zip(scaled, rows):
        assert actual == pytest.approx(expected)


def test_temperature_fit_is_deterministic_and_never_worse_than_identity():
    rows = [(0.8, 0.1, 0.1)] * 20 + [(0.1, 0.8, 0.1)] * 20
    outcomes = [1] * 20 + [0] * 20
    first = fit_temperature(rows, outcomes)
    second = fit_temperature(rows, outcomes)
    assert first == second
    assert first.log_loss_after <= first.log_loss_before
    assert 0.25 <= first.temperature <= 4.0


def test_temperature_fit_requires_enough_inner_oof_samples():
    with pytest.raises(ValueError, match="inner OOF"):
        fit_temperature([(0.5, 0.5)] * 10, [0] * 10)


def test_temperature_fit_rejects_invalid_probability_rows():
    with pytest.raises(ValueError, match="sum to one"):
        fit_temperature([(0.8, 0.8)] * 30, [0] * 30)


def test_temperature_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        apply_temperature([(0.5, 0.5)], 0.0)
