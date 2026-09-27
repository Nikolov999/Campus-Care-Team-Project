from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from campuscare.config import Settings
from campuscare.database import build_engine, create_session_factory, initialise_database
from campuscare.models import User
from campuscare.services import create_donation, register_user


def main() -> None:
    settings = Settings.from_env()
    engine = build_engine(settings.database_url)
    initialise_database(engine)
    factory = create_session_factory(engine)

    try:
        with factory.begin() as session:
            existing = session.scalar(select(User).where(User.email == "demo@student.ncirl.ie"))
            if existing:
                print("Demo data already exists.")
                return

            donor = register_user(
                session,
                first_name="CampusCare",
                last_name="Demo",
                email="demo@student.ncirl.ie",
                password="Campus123",
                allowed_domains=settings.allowed_email_domains,
                course="BSc (Hons) in Computing",
                year_of_study="Year 2",
            )
            create_donation(
                session,
                donor_id=donor.id,
                title="Scientific calculator",
                description="Working scientific calculator with a protective cover. Batteries included.",
                category="Books & Study",
                condition="Good",
                pickup_location="NCI reception",
            )
            create_donation(
                session,
                donor_id=donor.id,
                title="Winter jacket",
                description="Warm black winter jacket, size medium, recently washed and in excellent condition.",
                category="Clothing",
                condition="Excellent",
                pickup_location="NCI main entrance",
            )
    finally:
        engine.dispose()

    print("Demo account created: demo@student.ncirl.ie / Campus123")


if __name__ == "__main__":
    main()
