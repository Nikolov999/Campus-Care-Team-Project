from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from campuscare.config import Settings
from campuscare.database import build_engine

EXPECTED_TABLES = {"users", "donation_items", "reservations"}


def main() -> None:
    settings = Settings.from_env()
    engine = build_engine(settings.database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        tables = set(inspect(engine).get_table_names())
        missing = EXPECTED_TABLES - tables
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise RuntimeError(f"Database connection works, but tables are missing: {missing_text}")
    finally:
        engine.dispose()

    print("Database connection: OK")
    print("Required tables: OK")
    print(f"Database type: {settings.database_url.split(':', 1)[0]}")


if __name__ == "__main__":
    main()
