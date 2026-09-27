from __future__ import annotations

import pytest
from sqlalchemy import inspect, select

from campuscare.database import (
    build_engine,
    create_session_factory,
    initialise_database,
    session_scope,
)
from campuscare.models import User
from campuscare.security import hash_password


def test_database_initialisation_and_session_commit(tmp_path) -> None:
    engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'database.db'}")
    initialise_database(engine)
    factory = create_session_factory(engine)

    with session_scope(factory) as session:
        session.add(
            User(
                first_name="Database",
                last_name="Tester",
                email="database@student.ncirl.ie",
                password_hash=hash_password("Campus123"),
            )
        )

    with factory() as session:
        assert session.scalar(select(User).where(User.email == "database@student.ncirl.ie"))

    assert {"users", "donation_items", "reservations"}.issubset(
        set(inspect(engine).get_table_names())
    )
    engine.dispose()


def test_session_scope_rolls_back_on_error(tmp_path) -> None:
    engine = build_engine(f"sqlite+pysqlite:///{tmp_path / 'rollback.db'}")
    initialise_database(engine)
    factory = create_session_factory(engine)

    with pytest.raises(RuntimeError, match="force rollback"):
        with session_scope(factory) as session:
            session.add(
                User(
                    first_name="Rollback",
                    last_name="Tester",
                    email="rollback@student.ncirl.ie",
                    password_hash=hash_password("Campus123"),
                )
            )
            raise RuntimeError("force rollback")

    with factory() as session:
        assert session.scalar(select(User).where(User.email == "rollback@student.ncirl.ie")) is None
    engine.dispose()
