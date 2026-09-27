from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from campuscare.config import Settings
from campuscare.database import build_engine, initialise_database


def main() -> None:
    settings = Settings.from_env()
    engine = build_engine(settings.database_url)
    try:
        initialise_database(engine)
    finally:
        engine.dispose()
    print("CampusCare database schema is ready.")


if __name__ == "__main__":
    main()
