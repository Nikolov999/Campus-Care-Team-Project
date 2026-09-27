from __future__ import annotations

from datetime import timezone
from html import escape

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from campuscare.config import Settings
from campuscare.constants import CATEGORIES, CONDITIONS, STATUS_LABELS
from campuscare.services import (
    ServiceError,
    browse_items,
    cancel_reservation,
    complete_handover,
    create_donation,
    dashboard_metrics,
    get_user,
    list_user_donations,
    list_user_reservations,
    recalculate_trust_score,
    reopen_donation,
    reserve_item,
    update_profile,
    withdraw_donation,
)
from campuscare.ui.components import hero, item_summary_html, profile_header, status_pill


def _format_date(value) -> str:
    if not value:
        return "Unknown"
    try:
        return value.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return value.strftime("%d %b %Y")


# Render the landing dashboard with community metrics and the latest available donations.
def dashboard_page(factory: sessionmaker[Session], user_id: int) -> None:
    hero(
        "Give useful items a second life.",
        "Donate, discover and reserve reusable items within the NCI student community.",
        "Student-to-student reuse",
    )
    with factory() as session:
        metrics = dashboard_metrics(session)
        recent = browse_items(session, status="available", exclude_donor_id=user_id, limit=6)

    cols = st.columns(4)
    cols[0].metric("Available items", metrics.available_items)
    cols[1].metric("Completed donations", metrics.completed_donations)
    cols[2].metric("Active reservations", metrics.active_reservations)
    cols[3].metric("Community members", metrics.community_members)

    st.subheader("Recently added")
    if not recent:
        st.info("No available donations yet. The first listing can be added from Donate an Item.")
        return

    for row_start in range(0, len(recent), 3):
        row = st.columns(3)
        for col, item in zip(row, recent[row_start : row_start + 3]):
            with col:
                if item.image_data:
                    st.image(item.image_data, width="stretch")
                st.markdown(item_summary_html(item), unsafe_allow_html=True)
                if st.button("Open item", key=f"dashboard-open-{item.id}", width="stretch"):
                    st.session_state["selected_item_id"] = item.id
                    st.session_state["_nav_override"] = "Browse Items"
                    st.rerun()


# Present searchable donation listings and handle the user's reservation action.
def browse_page(factory: sessionmaker[Session], user_id: int) -> None:
    st.title("Browse Donations")
    st.caption("Search available items and reserve one directly from the listing.")

    filter_cols = st.columns([2.2, 1, 1])
    search_text = filter_cols[0].text_input("Search", placeholder="Laptop bag, textbook, kettle...")
    category = filter_cols[1].selectbox("Category", ("All",) + CATEGORIES)
    condition = filter_cols[2].selectbox("Condition", ("All",) + CONDITIONS)

    with factory() as session:
        items = browse_items(
            session,
            search_text=search_text,
            category=category,
            condition=condition,
            status="available",
            exclude_donor_id=user_id,
        )

    if not items:
        st.info("No available items match these filters.")
        return

    selected_id = st.session_state.pop("selected_item_id", None)
    for item in items:
        with st.container(border=True):
            left, right = st.columns([1, 2.2])
            with left:
                if item.image_data:
                    st.image(item.image_data, width="stretch")
                else:
                    st.markdown(
                        "<div class='cc-card' style='display:grid;place-items:center;min-height:190px;'>No image</div>",
                        unsafe_allow_html=True,
                    )
            with right:
                st.markdown(item_summary_html(item), unsafe_allow_html=True)
                action_cols = st.columns([1, 1, 2])
                if action_cols[0].button(
                    "Reserve",
                    key=f"reserve-{item.id}",
                    type="primary",
                    width="stretch",
                ):
                    try:
                        with factory.begin() as session:
                            reserve_item(session, item_id=item.id, receiver_id=user_id)
                        st.success("Item reserved. The donor can now arrange the handover with you.")
                        st.rerun()
                    except ServiceError as exc:
                        st.error(str(exc))
                if action_cols[1].button(
                    "Details", key=f"details-{item.id}", width="stretch"
                ):
                    st.session_state[f"show-details-{item.id}"] = not st.session_state.get(
                        f"show-details-{item.id}", False
                    )
                if selected_id == item.id:
                    st.session_state[f"show-details-{item.id}"] = True

                if st.session_state.get(f"show-details-{item.id}", False):
                    st.divider()
                    st.markdown("**Full description:**")
                    st.write(item.description)
                    st.markdown("**Pickup location:**")
                    st.write(item.pickup_location)
                    st.markdown(f"**Posted:** {_format_date(item.created_at)}")
                    st.markdown(f"**Donor trust score:** {item.donor.trust_score}/100")


# Collect and submit a new donation, including its optional image upload.
def donate_page(factory: sessionmaker[Session], user_id: int, settings: Settings) -> None:
    st.title("Donate an Item")
    st.caption("List a usable item for another NCI student. All donations are free.")

    with st.form("donation-form", clear_on_submit=True):
        title = st.text_input("Item title", max_chars=140, placeholder="Scientific calculator")
        category = st.selectbox("Category", CATEGORIES)
        condition = st.selectbox("Condition", CONDITIONS)
        pickup_location = st.text_input(
            "Preferred pickup location", max_chars=160, placeholder="NCI reception"
        )
        description = st.text_area(
            "Description",
            max_chars=2_000,
            height=150,
            placeholder="Describe the item, what is included and any marks or faults.",
        )
        upload = st.file_uploader(
            "Optional image",
            type=("png", "jpg", "jpeg", "webp"),
            help=f"Maximum size: {settings.max_upload_bytes // (1024 * 1024)} MB",
        )
        submitted = st.form_submit_button("Publish donation", key="donation-submit", type="primary", width="stretch")

    if not submitted:
        return

    image_data = None
    image_mime = None
    if upload is not None:
        image_data = upload.getvalue()
        image_mime = upload.type
        if len(image_data) > settings.max_upload_bytes:
            st.error("The image is larger than the configured upload limit.")
            return

    try:
        with factory.begin() as session:
            item = create_donation(
                session,
                donor_id=user_id,
                title=title,
                description=description,
                category=category,
                condition=condition,
                pickup_location=pickup_location,
                image_data=image_data,
                image_mime=image_mime,
                max_upload_bytes=settings.max_upload_bytes,
            )
        st.success(f"{item.title} is now visible in the donation feed.")
    except ServiceError as exc:
        st.error(str(exc))


def activity_page(factory: sessionmaker[Session], user_id: int) -> None:
    st.title("My Activity")
    donation_tab, reservation_tab = st.tabs(("My Donations", "My Reservations"))

    with factory() as session:
        donations = list_user_donations(session, user_id)
        reservations = list_user_reservations(session, user_id)

    with donation_tab:
        if not donations:
            st.info("You have not listed any donations yet.")
        for item in donations:
            with st.container(border=True):
                st.markdown(
                    f"### {escape(item.title)} {status_pill(item.status)}",
                    unsafe_allow_html=True,
                )
                st.caption(f"{item.category} · {item.condition} · Posted {_format_date(item.created_at)}")
                active = next((r for r in item.reservations if r.status == "active"), None)
                if active and active.receiver:
                    st.write(f"Reserved by: **{active.receiver.full_name}** ({active.receiver.email})")

                actions = st.columns(4)
                if item.status == "reserved":
                    if actions[0].button(
                        "Complete handover",
                        key=f"complete-{item.id}",
                        type="primary",
                        width="stretch",
                    ):
                        try:
                            with factory.begin() as session:
                                complete_handover(session, item_id=item.id, donor_id=user_id)
                            st.success("Handover completed and trust scores updated.")
                            st.rerun()
                        except ServiceError as exc:
                            st.error(str(exc))
                    if actions[1].button(
                        "Make available again",
                        key=f"reopen-{item.id}",
                        width="stretch",
                    ):
                        try:
                            with factory.begin() as session:
                                reopen_donation(session, item_id=item.id, donor_id=user_id)
                            st.rerun()
                        except ServiceError as exc:
                            st.error(str(exc))
                elif item.status in {"available", "withdrawn"}:
                    if item.status == "withdrawn":
                        if actions[0].button(
                            "Relist",
                            key=f"relist-{item.id}",
                            type="primary",
                            width="stretch",
                        ):
                            try:
                                with factory.begin() as session:
                                    reopen_donation(session, item_id=item.id, donor_id=user_id)
                                st.rerun()
                            except ServiceError as exc:
                                st.error(str(exc))
                    if item.status == "available" and actions[1].button(
                        "Withdraw",
                        key=f"withdraw-{item.id}",
                        width="stretch",
                    ):
                        try:
                            with factory.begin() as session:
                                withdraw_donation(session, item_id=item.id, donor_id=user_id)
                            st.rerun()
                        except ServiceError as exc:
                            st.error(str(exc))

    with reservation_tab:
        if not reservations:
            st.info("You have not reserved any items yet.")
        for reservation in reservations:
            item = reservation.item
            with st.container(border=True):
                st.markdown(f"### {item.title}")
                st.caption(
                    f"Reservation: {reservation.status.title()} · Item: {STATUS_LABELS.get(item.status, item.status.title())}"
                )
                st.write(f"Donor: **{item.donor.full_name}** ({item.donor.email})")
                st.write(f"Pickup: **{item.pickup_location}**")
                if reservation.status == "active":
                    if st.button(
                        "Cancel reservation",
                        key=f"cancel-reservation-{reservation.id}",
                    ):
                        try:
                            with factory.begin() as session:
                                cancel_reservation(
                                    session,
                                    reservation_id=reservation.id,
                                    receiver_id=user_id,
                                )
                            st.rerun()
                        except ServiceError as exc:
                            st.error(str(exc))


def profile_page(factory: sessionmaker[Session], user_id: int) -> None:
    with factory.begin() as session:
        recalculate_trust_score(session, user_id)
        user = get_user(session, user_id)
    if not user:
        st.error("The current user account could not be loaded.")
        return

    st.title("Profile")
    left, right = st.columns([1, 1.6])
    with left:
        profile_header(user)
        if user.bio:
            st.markdown("#### About")
            st.write(user.bio)
    with right:
        st.subheader("Edit profile")
        with st.form("profile-form"):
            first_name = st.text_input("First name", value=user.first_name, max_chars=80)
            last_name = st.text_input("Last name", value=user.last_name, max_chars=80)
            course = st.text_input("Course", value=user.course or "", max_chars=120)
            year = st.selectbox(
                "Year of study",
                ("", "Year 1", "Year 2", "Year 3", "Year 4", "Postgraduate"),
                index=("", "Year 1", "Year 2", "Year 3", "Year 4", "Postgraduate").index(user.year_of_study)
                if user.year_of_study in ("", "Year 1", "Year 2", "Year 3", "Year 4", "Postgraduate")
                else 0,
            )
            bio = st.text_area("Bio", value=user.bio or "", max_chars=500, height=130)
            submitted = st.form_submit_button("Save profile", key="profile-submit", type="primary", width="stretch")
        if submitted:
            try:
                with factory.begin() as session:
                    update_profile(
                        session,
                        user_id,
                        first_name=first_name,
                        last_name=last_name,
                        course=course,
                        year_of_study=year,
                        bio=bio,
                    )
                st.success("Profile updated.")
                st.rerun()
            except ServiceError as exc:
                st.error(str(exc))
