from __future__ import annotations

from sqlalchemy.dialects import postgresql

from campuscare.services import (
    _active_reservations_lock_statement,
    _item_lock_statement,
    _reservation_lock_statement,
)


def _compile(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).upper()


def test_item_lock_targets_only_donation_items() -> None:
    sql = _compile(_item_lock_statement(1))
    assert "LEFT OUTER JOIN" not in sql
    assert "FOR UPDATE OF DONATION_ITEMS" in sql


def test_reservation_lock_targets_only_reservations() -> None:
    sql = _compile(_reservation_lock_statement(1))
    assert "LEFT OUTER JOIN" not in sql
    assert "FOR UPDATE OF RESERVATIONS" in sql


def test_active_reservation_lock_avoids_outer_join() -> None:
    sql = _compile(_active_reservations_lock_statement(1))
    assert "LEFT OUTER JOIN" not in sql
    assert "FOR UPDATE OF RESERVATIONS" in sql
    assert "RESERVATIONS.STATUS = 'ACTIVE'" in sql
