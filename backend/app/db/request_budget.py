"""Atomic, durable provider-request budget reservations."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import psycopg


class RequestBudgetError(RuntimeError):
    """Raised when a provider request cannot safely be reserved."""


class RequestBudgetExceeded(RequestBudgetError):
    """Raised when the persisted request ceiling has been reached."""


class ReservationConflict(RequestBudgetError):
    """Raised when an idempotency key is reused with different request data."""


@dataclass(frozen=True)
class RequestReservation:
    """A durable reservation; only newly created reservations may send HTTP."""

    reservation_id: int
    created: bool


class PostgresRequestBudget:
    """Reserve quota in PostgreSQL before making an external provider call.

    Use a dedicated connection with autocommit=True. Each new reservation is
    committed independently, so process interruption never refunds a request.
    The import-run row lock serializes all reservations for a run, including
    duplicate idempotency keys submitted concurrently.
    """

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        if not connection.autocommit:
            raise RequestBudgetError("DEDICATED_AUTOCOMMIT_CONNECTION_REQUIRED")
        self.connection = connection

    @staticmethod
    def _canonical_params(params: dict[str, Any]) -> str:
        try:
            payload = json.dumps(
                params, sort_keys=True, separators=(",", ":"), allow_nan=False
            )
        except (TypeError, ValueError):
            raise RequestBudgetError("REQUEST_PARAMS_MUST_BE_FINITE_JSON") from None
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def callback_for_run(self, import_run_id: int):
        """Build the provider adapter callback bound to this import run."""

        def reserve_request(
            request_key: str,
            window_start: datetime,
            window_end: datetime,
            page_number: int,
            endpoint: str,
            request_params: Any,
        ) -> bool:
            reservation = self.reserve(
                import_run_id=import_run_id,
                request_key=request_key,
                window_start=window_start,
                window_end=window_end,
                page_number=page_number,
                endpoint=endpoint,
                request_params=dict(request_params),
            )
            return reservation.created

        return reserve_request

    def reserve(
        self,
        *,
        import_run_id: int,
        request_key: str,
        window_start: datetime,
        window_end: datetime,
        page_number: int,
        endpoint: str,
        request_params: dict[str, Any],
        reserved_at: datetime | None = None,
    ) -> RequestReservation:
        for field, value in (
            ("WINDOW_START", window_start),
            ("WINDOW_END", window_end),
            ("RESERVED_AT", reserved_at),
        ):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise RequestBudgetError(f"{field}_MUST_BE_TIMEZONE_AWARE")
        if (
            not request_key.strip()
            or page_number < 1
            or window_end <= window_start
            or not endpoint.startswith("/")
            or "?" in endpoint
        ):
            raise RequestBudgetError("INVALID_REQUEST_RESERVATION")
        params_hash = self._canonical_params(request_params)
        timestamp = reserved_at or datetime.now(UTC)

        with self.connection.transaction():
            state = self.connection.execute(
                """
                SELECT status, requests_used, request_budget
                FROM veltrix_ai_analyst.import_runs
                WHERE id = %s
                FOR UPDATE
                """,
                (import_run_id,),
            ).fetchone()
            if state is None:
                raise RequestBudgetError("IMPORT_RUN_NOT_FOUND")

            existing = self.connection.execute(
                """
                SELECT id, window_start, window_end, page_number, endpoint, params_sha256
                FROM veltrix_ai_analyst.import_request_reservations
                WHERE import_run_id = %s AND request_key = %s
                """,
                (import_run_id, request_key),
            ).fetchone()
            if existing is not None:
                expected = (window_start, window_end, page_number, endpoint, params_hash)
                if tuple(existing[1:]) != expected:
                    raise ReservationConflict("REQUEST_KEY_REUSED_WITH_DIFFERENT_PAYLOAD")
                return RequestReservation(int(existing[0]), created=False)

            if state[0] != "RUNNING":
                raise RequestBudgetError("IMPORT_RUN_NOT_RUNNING")
            if state[1] >= state[2]:
                raise RequestBudgetExceeded("PERSISTED_REQUEST_BUDGET_EXHAUSTED")

            updated = self.connection.execute(
                """
                UPDATE veltrix_ai_analyst.import_runs
                SET requests_used = requests_used + 1
                WHERE id = %s AND status = 'RUNNING'
                  AND requests_used < request_budget
                RETURNING requests_used
                """,
                (import_run_id,),
            ).fetchone()
            if updated is None:
                raise RequestBudgetExceeded("PERSISTED_REQUEST_BUDGET_EXHAUSTED")

            row = self.connection.execute(
                """
                INSERT INTO veltrix_ai_analyst.import_request_reservations (
                    import_run_id, request_key, window_start, window_end,
                    page_number, endpoint, params_sha256, reserved_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    import_run_id, request_key, window_start, window_end,
                    page_number, endpoint, params_hash, timestamp,
                ),
            ).fetchone()
            if row is None:
                raise RequestBudgetError("REQUEST_RESERVATION_INSERT_FAILED")
            return RequestReservation(int(row[0]), created=True)
