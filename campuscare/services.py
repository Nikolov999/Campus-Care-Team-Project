from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, lazyload

from campuscare.constants import CATEGORIES, CONDITIONS
from campuscare.models import DonationItem, Reservation, User
from campuscare.security import hash_password, normalise_email, validate_allowed_email, verify_password

# This module is the service layer: it centralises business rules and database operations
# so Streamlit pages can focus on collecting input and presenting results.
DEFAULT_MAX_UPLOAD_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/webp"}


class ServiceError(ValueError):
    pass


@dataclass(frozen=True)
class DashboardMetrics:
    available_items: int
    completed_donations: int
    active_reservations: int
    community_members: int


def register_user(
    session: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    allowed_domains: tuple[str, ...],
    course: str | None = None,
    year_of_study: str | None = None,
) -> User:
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name:
        raise ServiceError("First name and last name are required.")
    if len(first_name) > 80 or len(last_name) > 80:
        raise ServiceError("Names must be 80 characters or fewer.")

    course = (course or "").strip()
    year_of_study = (year_of_study or "").strip()
    if len(course) > 120:
        raise ServiceError("Course must be 120 characters or fewer.")
    if len(year_of_study) > 40:
        raise ServiceError("Year of study must be 40 characters or fewer.")

    email = validate_allowed_email(email, allowed_domains)
    existing = session.scalar(select(User).where(User.email == email))
    if existing:
        raise ServiceError("An account already exists for this email address.")

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hash_password(password),
        course=course or None,
        year_of_study=year_of_study or None,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:
        raise ServiceError("An account already exists for this email address.") from exc
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    email = normalise_email(email)
    user = session.scalar(select(User).where(User.email == email))
    if user and verify_password(password, user.password_hash):
        return user
    return None


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def update_profile(
    session: Session,
    user_id: int,
    *,
    first_name: str,
    last_name: str,
    course: str,
    year_of_study: str,
    bio: str,
) -> User:
    user = session.get(User, user_id)
    if not user:
        raise ServiceError("User account was not found.")

    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name:
        raise ServiceError("First name and last name are required.")
    if len(first_name) > 80 or len(last_name) > 80:
        raise ServiceError("Names must be 80 characters or fewer.")

    course = course.strip()
    year_of_study = year_of_study.strip()
    bio = bio.strip()
    if len(course) > 120:
        raise ServiceError("Course must be 120 characters or fewer.")
    if len(year_of_study) > 40:
        raise ServiceError("Year of study must be 40 characters or fewer.")
    if len(bio) > 500:
        raise ServiceError("Bio must be 500 characters or fewer.")

    user.first_name = first_name
    user.last_name = last_name
    user.course = course or None
    user.year_of_study = year_of_study or None
    user.bio = bio or None
    session.flush()
    return user


def _detect_image_mime(image_data: bytes) -> str | None:
    if image_data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(image_data) >= 12 and image_data[:4] == b"RIFF" and image_data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _validate_image_upload(
    image_data: bytes | None,
    image_mime: str | None,
    max_upload_bytes: int,
) -> tuple[bytes | None, str | None]:
    if image_data is None:
        if image_mime:
            raise ServiceError("Image type was supplied without image data.")
        return None, None
    if not image_data:
        raise ServiceError("The uploaded image is empty.")
    if len(image_data) > max_upload_bytes:
        raise ServiceError("The image is larger than the configured upload limit.")

    claimed_mime = (image_mime or "").lower().strip()
    detected_mime = _detect_image_mime(image_data)
    if claimed_mime not in ALLOWED_IMAGE_MIMES or detected_mime != claimed_mime:
        raise ServiceError("Upload a valid PNG, JPEG or WebP image.")
    return image_data, claimed_mime


def create_donation(
    session: Session,
    *,
    donor_id: int,
    title: str,
    description: str,
    category: str,
    condition: str,
    pickup_location: str,
    image_data: bytes | None = None,
    image_mime: str | None = None,
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
) -> DonationItem:
    title = title.strip()
    description = description.strip()
    pickup_location = pickup_location.strip()

    if not title or len(title) < 3:
        raise ServiceError("Item title must contain at least 3 characters.")
    if len(title) > 140:
        raise ServiceError("Item title must be 140 characters or fewer.")
    if not description or len(description) < 10:
        raise ServiceError("Description must contain at least 10 characters.")
    if len(description) > 2_000:
        raise ServiceError("Description must be 2,000 characters or fewer.")
    if category not in CATEGORIES:
        raise ServiceError("Select a valid category.")
    if condition not in CONDITIONS:
        raise ServiceError("Select a valid item condition.")
    if not pickup_location:
        raise ServiceError("Pickup location is required.")
    if len(pickup_location) > 160:
        raise ServiceError("Pickup location must be 160 characters or fewer.")
    if not session.get(User, donor_id):
        raise ServiceError("Donor account was not found.")
    image_data, image_mime = _validate_image_upload(
        image_data, image_mime, max_upload_bytes
    )

    item = DonationItem(
        donor_id=donor_id,
        title=title,
        description=description,
        category=category,
        condition=condition,
        pickup_location=pickup_location,
        status="available",
        image_data=image_data,
        image_mime=image_mime,
    )
    session.add(item)
    session.flush()
    return item


def browse_items(
    session: Session,
    *,
    search_text: str = "",
    category: str = "All",
    condition: str = "All",
    status: str = "available",
    exclude_donor_id: int | None = None,
    limit: int = 100,
) -> list[DonationItem]:
    stmt = (
        select(DonationItem)
        .options(joinedload(DonationItem.donor))
        .order_by(DonationItem.created_at.desc())
        .limit(limit)
    )

    if status != "All":
        stmt = stmt.where(DonationItem.status == status)
    if category != "All":
        stmt = stmt.where(DonationItem.category == category)
    if condition != "All":
        stmt = stmt.where(DonationItem.condition == condition)
    if exclude_donor_id is not None:
        stmt = stmt.where(DonationItem.donor_id != exclude_donor_id)

    search_text = search_text.strip()
    if search_text:
        needle = f"%{search_text.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(DonationItem.title).like(needle),
                func.lower(DonationItem.description).like(needle),
                func.lower(DonationItem.pickup_location).like(needle),
            )
        )

    return list(session.scalars(stmt).unique())


def get_item(session: Session, item_id: int) -> DonationItem | None:
    stmt = (
        select(DonationItem)
        .options(
            joinedload(DonationItem.donor),
            joinedload(DonationItem.reservations).joinedload(Reservation.receiver),
        )
        .where(DonationItem.id == item_id)
    )
    return session.scalar(stmt)


def _item_lock_statement(item_id: int):
    return (
        select(DonationItem)
        .options(lazyload("*"))
        .where(DonationItem.id == item_id)
        .with_for_update(of=DonationItem)
    )


def _reservation_lock_statement(reservation_id: int):
    return (
        select(Reservation)
        .options(lazyload("*"))
        .where(Reservation.id == reservation_id)
        .with_for_update(of=Reservation)
    )


def _active_reservations_lock_statement(item_id: int):
    return (
        select(Reservation)
        .options(lazyload("*"))
        .where(
            Reservation.item_id == item_id,
            Reservation.status == "active",
        )
        .with_for_update(of=Reservation)
    )


def _lock_item(session: Session, item_id: int) -> DonationItem | None:
    """Lock only the donation_items row, never eagerly joined relationships.

    PostgreSQL rejects a bare FOR UPDATE when SQLAlchemy has added a LEFT OUTER
    JOIN for relationship loading. lazyload("*") keeps the lock query focused
    on the parent table, while ``of=DonationItem`` explicitly scopes the lock.
    """
    return session.scalar(_item_lock_statement(item_id))


def _lock_reservation(session: Session, reservation_id: int) -> Reservation | None:
    """Lock only the reservations row without joining its related item."""
    return session.scalar(_reservation_lock_statement(reservation_id))


def reserve_item(session: Session, *, item_id: int, receiver_id: int) -> Reservation:
    # Validate the complete reservation workflow here so every caller follows the same rules.
    item = _lock_item(session, item_id)
    if not item:
        raise ServiceError("Donation item was not found.")
    if not session.get(User, receiver_id):
        raise ServiceError("Receiver account was not found.")
    if item.donor_id == receiver_id:
        raise ServiceError("You cannot reserve your own donation.")
    if item.status != "available":
        raise ServiceError("This item is no longer available.")

    active = session.scalar(
        select(Reservation).where(
            Reservation.item_id == item_id,
            Reservation.status == "active",
        )
    )
    if active:
        raise ServiceError("This item already has an active reservation.")

    reservation = Reservation(
        item_id=item_id,
        receiver_id=receiver_id,
        status="active",
    )
    item.status = "reserved"
    session.add(reservation)
    session.flush()
    return reservation


def cancel_reservation(session: Session, *, reservation_id: int, receiver_id: int) -> None:
    # Read the foreign key first, then lock in a consistent order: item -> reservation.
    # This matches the order used by complete/reopen/withdraw and reduces deadlock risk.
    item_id = session.scalar(
        select(Reservation.item_id).where(Reservation.id == reservation_id)
    )
    if item_id is None:
        raise ServiceError("Reservation was not found.")

    item = _lock_item(session, item_id)
    reservation = _lock_reservation(session, reservation_id)
    if not reservation or not item:
        raise ServiceError("Reservation was not found.")
    if reservation.receiver_id != receiver_id:
        raise ServiceError("You cannot cancel another user's reservation.")
    if reservation.status != "active":
        raise ServiceError("Only active reservations can be cancelled.")

    reservation.status = "cancelled"
    reservation.cancelled_by = "receiver"
    item.status = "available"
    session.flush()
    recalculate_trust_score(session, receiver_id)


def complete_handover(session: Session, *, item_id: int, donor_id: int) -> None:
    item = _lock_item(session, item_id)
    if not item:
        raise ServiceError("Donation item was not found.")
    if item.donor_id != donor_id:
        raise ServiceError("Only the donor can complete the handover.")
    if item.status != "reserved":
        raise ServiceError("The item must be reserved before handover can be completed.")

    active = session.scalar(
        _active_reservations_lock_statement(item_id)
    )
    if not active:
        raise ServiceError("No active reservation exists for this item.")

    item.status = "completed"
    active.status = "completed"
    session.flush()
    recalculate_trust_score(session, donor_id)
    recalculate_trust_score(session, active.receiver_id)


def reopen_donation(session: Session, *, item_id: int, donor_id: int) -> None:
    item = _lock_item(session, item_id)
    if not item:
        raise ServiceError("Donation item was not found.")
    if item.donor_id != donor_id:
        raise ServiceError("Only the donor can update this item.")
    if item.status not in {"reserved", "withdrawn"}:
        raise ServiceError("Only reserved or withdrawn items can be reopened.")

    active_reservations = list(
        session.scalars(
            _active_reservations_lock_statement(item_id)
        )
    )
    for reservation in active_reservations:
        reservation.status = "cancelled"
        reservation.cancelled_by = "donor"
    item.status = "available"
    session.flush()


def withdraw_donation(session: Session, *, item_id: int, donor_id: int) -> None:
    item = _lock_item(session, item_id)
    if not item:
        raise ServiceError("Donation item was not found.")
    if item.donor_id != donor_id:
        raise ServiceError("Only the donor can withdraw this item.")
    if item.status == "completed":
        raise ServiceError("Completed donations cannot be withdrawn.")

    active_reservations = list(
        session.scalars(
            _active_reservations_lock_statement(item_id)
        )
    )
    for reservation in active_reservations:
        reservation.status = "cancelled"
        reservation.cancelled_by = "donor"
    item.status = "withdrawn"
    session.flush()


def list_user_donations(session: Session, user_id: int) -> list[DonationItem]:
    stmt = (
        select(DonationItem)
        .options(joinedload(DonationItem.reservations).joinedload(Reservation.receiver))
        .where(DonationItem.donor_id == user_id)
        .order_by(DonationItem.created_at.desc())
    )
    return list(session.scalars(stmt).unique())


def list_user_reservations(session: Session, user_id: int) -> list[Reservation]:
    stmt = (
        select(Reservation)
        .options(
            joinedload(Reservation.item).joinedload(DonationItem.donor),
        )
        .where(Reservation.receiver_id == user_id)
        .order_by(Reservation.created_at.desc())
    )
    return list(session.scalars(stmt).unique())


def recalculate_trust_score(session: Session, user_id: int) -> int:
    user = session.get(User, user_id)
    if not user:
        raise ServiceError("User account was not found.")

    donated = session.scalar(
        select(func.count(DonationItem.id)).where(
            DonationItem.donor_id == user_id,
            DonationItem.status == "completed",
        )
    ) or 0
    received = session.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.receiver_id == user_id,
            Reservation.status == "completed",
        )
    ) or 0
    cancelled = session.scalar(
        select(func.count(Reservation.id)).where(
            Reservation.receiver_id == user_id,
            Reservation.status == "cancelled",
            Reservation.cancelled_by == "receiver",
        )
    ) or 0

    score = max(0, min(100, 50 + donated * 5 + received * 3 - cancelled * 2))
    user.trust_score = score
    session.flush()
    return score


def dashboard_metrics(session: Session) -> DashboardMetrics:
    return DashboardMetrics(
        available_items=session.scalar(
            select(func.count(DonationItem.id)).where(DonationItem.status == "available")
        )
        or 0,
        completed_donations=session.scalar(
            select(func.count(DonationItem.id)).where(DonationItem.status == "completed")
        )
        or 0,
        active_reservations=session.scalar(
            select(func.count(Reservation.id)).where(Reservation.status == "active")
        )
        or 0,
        community_members=session.scalar(select(func.count(User.id))) or 0,
    )
