from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("trust_score BETWEEN 0 AND 100", name="ck_users_trust_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    course: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    year_of_study: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    trust_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    donations: Mapped[list["DonationItem"]] = relationship(
        back_populates="donor", cascade="all, delete-orphan"
    )
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="receiver", cascade="all, delete-orphan"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class DonationItem(Base):
    __tablename__ = "donation_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'reserved', 'completed', 'withdrawn')",
            name="ck_donation_items_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    donor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    condition: Mapped[str] = mapped_column(String(40), nullable=False)
    pickup_location: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="available", index=True)
    image_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    image_mime: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    donor: Mapped[User] = relationship(back_populates="donations")
    reservations: Mapped[list["Reservation"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'cancelled', 'completed')",
            name="ck_reservations_status",
        ),
        CheckConstraint(
            "cancelled_by IS NULL OR cancelled_by IN ('receiver', 'donor')",
            name="ck_reservations_cancelled_by",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("donation_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receiver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active", index=True)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    item: Mapped[DonationItem] = relationship(back_populates="reservations")
    receiver: Mapped[User] = relationship(back_populates="reservations")


Index("ix_donation_items_status_category", DonationItem.status, DonationItem.category)
Index("ix_reservations_item_status", Reservation.item_id, Reservation.status)
Index(
    "uq_reservations_one_active_per_item",
    Reservation.item_id,
    unique=True,
    sqlite_where=Reservation.status == "active",
    postgresql_where=Reservation.status == "active",
)
