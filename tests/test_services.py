from __future__ import annotations

import base64

import pytest

from campuscare.models import DonationItem, Reservation, User
from campuscare.services import (
    ServiceError,
    authenticate_user,
    browse_items,
    cancel_reservation,
    complete_handover,
    create_donation,
    dashboard_metrics,
    list_user_donations,
    list_user_reservations,
    register_user,
    reopen_donation,
    reserve_item,
    update_profile,
    withdraw_donation,
)

DOMAINS = ("student.ncirl.ie", "ncirl.ie")
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def create_user(session, email: str, first_name: str = "Test") -> User:
    return register_user(
        session,
        first_name=first_name,
        last_name="Student",
        email=email,
        password="Campus123",
        allowed_domains=DOMAINS,
        course="Computing",
        year_of_study="Year 2",
    )


def create_item(session, donor_id: int, title: str = "Desk lamp") -> DonationItem:
    return create_donation(
        session,
        donor_id=donor_id,
        title=title,
        description="A working reusable item in good condition for another student.",
        category="Household",
        condition="Good",
        pickup_location="NCI reception",
    )


def test_register_and_authenticate(session_factory) -> None:
    with session_factory.begin() as session:
        user = create_user(session, "one@student.ncirl.ie")
        user_id = user.id

    with session_factory() as session:
        authenticated = authenticate_user(session, "ONE@student.ncirl.ie", "Campus123")
        assert authenticated is not None
        assert authenticated.id == user_id
        assert authenticate_user(session, "one@student.ncirl.ie", "Wrong123") is None


def test_duplicate_registration_rejected(session_factory) -> None:
    with session_factory.begin() as session:
        create_user(session, "duplicate@student.ncirl.ie")

    with pytest.raises(ServiceError, match="already exists"):
        with session_factory.begin() as session:
            create_user(session, "DUPLICATE@student.ncirl.ie")


def test_profile_update_validates_and_persists(session_factory) -> None:
    with session_factory.begin() as session:
        user = create_user(session, "profile@student.ncirl.ie")
        user_id = user.id

    with session_factory.begin() as session:
        update_profile(
            session,
            user_id,
            first_name="Updated",
            last_name="Name",
            course="Cybersecurity",
            year_of_study="Year 3",
            bio="Interested in sustainable technology.",
        )

    with session_factory() as session:
        user = session.get(User, user_id)
        assert user.full_name == "Updated Name"
        assert user.course == "Cybersecurity"
        assert user.bio == "Interested in sustainable technology."

    with pytest.raises(ServiceError, match="80 characters"):
        with session_factory.begin() as session:
            update_profile(
                session,
                user_id,
                first_name="A" * 81,
                last_name="Name",
                course="Computing",
                year_of_study="Year 2",
                bio="",
            )


def test_create_donation_with_valid_image(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "image@student.ncirl.ie")
        item = create_donation(
            session,
            donor_id=donor.id,
            title="Calculator",
            description="A working calculator with its protective cover included.",
            category="Books & Study",
            condition="Excellent",
            pickup_location="NCI library",
            image_data=PNG_1X1,
            image_mime="image/png",
            max_upload_bytes=1024 * 1024,
        )
        item_id = item.id

    with session_factory() as session:
        stored = session.get(DonationItem, item_id)
        assert stored.image_data == PNG_1X1
        assert stored.image_mime == "image/png"


def test_invalid_or_oversized_image_rejected(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "badimage@student.ncirl.ie")
        donor_id = donor.id

    with pytest.raises(ServiceError, match="valid PNG"):
        with session_factory.begin() as session:
            create_donation(
                session,
                donor_id=donor_id,
                title="Fake image",
                description="This item has an invalid image payload for testing.",
                category="Other",
                condition="Good",
                pickup_location="NCI reception",
                image_data=b"not-an-image",
                image_mime="image/png",
            )

    with pytest.raises(ServiceError, match="larger"):
        with session_factory.begin() as session:
            create_donation(
                session,
                donor_id=donor_id,
                title="Large image",
                description="This item has an image larger than the configured limit.",
                category="Other",
                condition="Good",
                pickup_location="NCI reception",
                image_data=PNG_1X1,
                image_mime="image/png",
                max_upload_bytes=8,
            )


def test_browse_search_filters_and_exclusion(session_factory) -> None:
    with session_factory.begin() as session:
        first = create_user(session, "first@student.ncirl.ie")
        second = create_user(session, "second@student.ncirl.ie")
        create_item(session, first.id, "Blue desk lamp")
        create_donation(
            session,
            donor_id=second.id,
            title="Python textbook",
            description="A clean Python textbook with no missing or damaged pages.",
            category="Books & Study",
            condition="Excellent",
            pickup_location="NCI library",
        )
        first_id = first.id

    with session_factory() as session:
        searched = browse_items(session, search_text="python")
        assert [item.title for item in searched] == ["Python textbook"]

        filtered = browse_items(session, category="Books & Study", condition="Excellent")
        assert [item.title for item in filtered] == ["Python textbook"]

        excluded = browse_items(session, exclude_donor_id=first_id)
        assert all(item.donor_id != first_id for item in excluded)


def test_reservation_and_handover_flow(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "donor@student.ncirl.ie", "Donor")
        receiver = create_user(session, "receiver@student.ncirl.ie", "Receiver")
        item = create_item(session, donor.id)
        donor_id, receiver_id, item_id = donor.id, receiver.id, item.id

    with session_factory.begin() as session:
        reservation = reserve_item(session, item_id=item_id, receiver_id=receiver_id)
        reservation_id = reservation.id

    with session_factory.begin() as session:
        complete_handover(session, item_id=item_id, donor_id=donor_id)

    with session_factory() as session:
        item = session.get(DonationItem, item_id)
        reservation = session.get(Reservation, reservation_id)
        donor = session.get(User, donor_id)
        receiver = session.get(User, receiver_id)
        assert item.status == "completed"
        assert reservation.status == "completed"
        assert donor.trust_score == 55
        assert receiver.trust_score == 53


def test_second_reservation_is_rejected(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "reserve-donor@student.ncirl.ie")
        first = create_user(session, "reserve-one@student.ncirl.ie")
        second = create_user(session, "reserve-two@student.ncirl.ie")
        item = create_item(session, donor.id)
        item_id, first_id, second_id = item.id, first.id, second.id

    with session_factory.begin() as session:
        reserve_item(session, item_id=item_id, receiver_id=first_id)

    with pytest.raises(ServiceError, match="no longer available"):
        with session_factory.begin() as session:
            reserve_item(session, item_id=item_id, receiver_id=second_id)


def test_user_cannot_reserve_own_item(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "owner@student.ncirl.ie")
        item = create_item(session, donor.id, "Textbook")
        donor_id, item_id = donor.id, item.id

    with pytest.raises(ServiceError, match="own donation"):
        with session_factory.begin() as session:
            reserve_item(session, item_id=item_id, receiver_id=donor_id)


def test_missing_receiver_rejected_cleanly(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "missing@student.ncirl.ie")
        item = create_item(session, donor.id)
        item_id = item.id

    with pytest.raises(ServiceError, match="Receiver account"):
        with session_factory.begin() as session:
            reserve_item(session, item_id=item_id, receiver_id=999999)


def test_cancel_reservation_reopens_item_and_updates_score(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "d@student.ncirl.ie")
        receiver = create_user(session, "r@student.ncirl.ie")
        item = create_item(session, donor.id, "Kettle")
        receiver_id, item_id = receiver.id, item.id

    with session_factory.begin() as session:
        reservation = reserve_item(session, item_id=item_id, receiver_id=receiver_id)
        reservation_id = reservation.id

    with session_factory.begin() as session:
        cancel_reservation(session, reservation_id=reservation_id, receiver_id=receiver_id)

    with session_factory() as session:
        assert session.get(DonationItem, item_id).status == "available"
        reservation = session.get(Reservation, reservation_id)
        receiver = session.get(User, receiver_id)
        assert reservation.status == "cancelled"
        assert reservation.cancelled_by == "receiver"
        assert receiver.trust_score == 48


def test_other_user_cannot_cancel_reservation(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "cancel-donor@student.ncirl.ie")
        receiver = create_user(session, "cancel-receiver@student.ncirl.ie")
        other = create_user(session, "cancel-other@student.ncirl.ie")
        item = create_item(session, donor.id)
        item_id, receiver_id, other_id = item.id, receiver.id, other.id

    with session_factory.begin() as session:
        reservation = reserve_item(session, item_id=item_id, receiver_id=receiver_id)
        reservation_id = reservation.id

    with pytest.raises(ServiceError, match="another user's"):
        with session_factory.begin() as session:
            cancel_reservation(session, reservation_id=reservation_id, receiver_id=other_id)


def test_donor_can_withdraw_and_relist(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "withdraw@student.ncirl.ie")
        item = create_item(session, donor.id)
        donor_id, item_id = donor.id, item.id

    with session_factory.begin() as session:
        withdraw_donation(session, item_id=item_id, donor_id=donor_id)
    with session_factory() as session:
        assert session.get(DonationItem, item_id).status == "withdrawn"

    with session_factory.begin() as session:
        reopen_donation(session, item_id=item_id, donor_id=donor_id)
    with session_factory() as session:
        assert session.get(DonationItem, item_id).status == "available"


def test_activity_lists_and_dashboard_metrics(session_factory) -> None:
    with session_factory.begin() as session:
        donor = create_user(session, "metrics-donor@student.ncirl.ie")
        receiver = create_user(session, "metrics-receiver@student.ncirl.ie")
        item = create_item(session, donor.id)
        donor_id, receiver_id, item_id = donor.id, receiver.id, item.id

    with session_factory.begin() as session:
        reserve_item(session, item_id=item_id, receiver_id=receiver_id)

    with session_factory() as session:
        donations = list_user_donations(session, donor_id)
        reservations = list_user_reservations(session, receiver_id)
        metrics = dashboard_metrics(session)
        assert len(donations) == 1
        assert len(reservations) == 1
        assert metrics.available_items == 0
        assert metrics.active_reservations == 1
        assert metrics.community_members == 2
