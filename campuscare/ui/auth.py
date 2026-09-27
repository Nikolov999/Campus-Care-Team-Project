from __future__ import annotations

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker

from campuscare.config import Settings
from campuscare.services import ServiceError, authenticate_user, register_user
from campuscare.ui.components import brand, hero


# Coordinate the guest interface for login and registration while delegating
# account validation and persistence to the service layer.
def authentication_screen(factory: sessionmaker[Session], settings: Settings) -> None:
    brand()
    hero(
        "Useful items. Shared locally.",
        "CampusCare connects NCI students who have reusable items with students who need them.",
        "Sustainable campus community",
    )

    login_tab, register_tab = st.tabs(("Log in", "Create account"))

    # Existing users are verified before their identifier is stored in session state.
    with login_tab:
        with st.form("login-form"):
            email = st.text_input("NCI email", key="login-email")
            password = st.text_input("Password", type="password", key="login-password")
            submitted = st.form_submit_button("Log in", key="login-submit", type="primary", width="stretch")
        if submitted:
            with factory() as session:
                user = authenticate_user(session, email, password)
            if not user:
                st.error("Email or password is incorrect.")
            else:
                # Session state allows Streamlit reruns to recognise the signed-in user.
                st.session_state["user_id"] = user.id
                st.session_state["_nav_override"] = "Home"
                st.rerun()

    # Registration collects account details and creates the user in one transaction.
    with register_tab:
        with st.form("register-form"):
            name_cols = st.columns(2)
            first_name = name_cols[0].text_input("First name", key="register-first-name")
            last_name = name_cols[1].text_input("Last name", key="register-last-name")
            email = st.text_input("NCI email", key="register-email")
            course = st.text_input("Course", placeholder="BSc (Hons) in Computing", key="register-course")
            year = st.selectbox(
                "Year of study",
                ("", "Year 1", "Year 2", "Year 3", "Year 4", "Postgraduate"),
                key="register-year",
            )
            password = st.text_input("Password", type="password", key="register-password")
            confirm = st.text_input("Confirm password", type="password", key="register-confirm")
            st.caption("Use at least 8 characters with one letter and one number.")
            submitted = st.form_submit_button("Create account", key="register-submit", type="primary", width="stretch")

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    with factory.begin() as session:
                        user = register_user(
                            session,
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            password=password,
                            allowed_domains=settings.allowed_email_domains,
                            course=course,
                            year_of_study=year,
                        )
                    st.session_state["user_id"] = user.id
                    st.session_state["_nav_override"] = "Home"
                    st.rerun()
                except (ServiceError, ValueError) as exc:
                    st.error(str(exc))
