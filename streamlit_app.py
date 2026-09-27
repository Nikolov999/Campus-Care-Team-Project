from __future__ import annotations

import os

import streamlit as st

from campuscare.config import ConfigurationError, Settings
from campuscare.database import build_engine, create_session_factory, initialise_database
from campuscare.services import get_user
from campuscare.ui.auth import authentication_screen
from campuscare.ui.components import brand
from campuscare.ui.pages import (
    activity_page,
    browse_page,
    dashboard_page,
    donate_page,
    profile_page,
)
from campuscare.ui.styles import apply_styles

# Main Streamlit entry point: configures the shared page shell before rendering any screen.
st.set_page_config(
    page_title="CampusCare",
    page_icon=":material/volunteer_activism:",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_styles()


@st.cache_resource(show_spinner=False)
def app_resources(settings: Settings):
    # Initialise long-lived database resources once and reuse them across Streamlit reruns.
    engine = build_engine(settings.database_url)
    initialise_database(engine)
    factory = create_session_factory(engine)
    return engine, factory


try:
    settings = Settings.from_env()
    engine, session_factory = app_resources(settings)
except ConfigurationError as exc:
    st.error(str(exc))
    st.code(
        "DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/campuscare",
        language="bash",
    )
    st.stop()
except Exception as exc:
    st.error("CampusCare could not connect to the configured database.")
    if os.getenv("APP_ENV", "development").lower() != "production":
        st.exception(exc)
    st.stop()

user_id = st.session_state.get("user_id")
# Authentication gates the rest of the application and stores the signed-in user in session state.
if not user_id:
    authentication_screen(session_factory, settings)
    st.stop()

with session_factory() as session:
    current_user = get_user(session, int(user_id))
if not current_user:
    st.session_state.clear()
    st.rerun()

with st.sidebar:
    brand(compact=True)
    st.caption(f"Signed in as {current_user.full_name}")
    navigation = ("Home", "Browse Items", "Donate an Item", "My Activity", "Profile")
    override = st.session_state.pop("_nav_override", None)
    if override in navigation:
        st.session_state["_nav_widget"] = override
    if st.session_state.get("_nav_widget") not in navigation:
        st.session_state["_nav_widget"] = "Home"
    selected = st.radio(
        "Navigation",
        navigation,
        key="_nav_widget",
        label_visibility="collapsed",
    )
    st.divider()
    st.caption(f"Trust score: {current_user.trust_score}/100")
    if st.button("Log out", width="stretch"):
        st.session_state.clear()
        st.rerun()

# Route the sidebar selection to the corresponding page while keeping this file as the navigation hub.
if selected == "Home":
    dashboard_page(session_factory, current_user.id)
elif selected == "Browse Items":
    browse_page(session_factory, current_user.id)
elif selected == "Donate an Item":
    donate_page(session_factory, current_user.id, settings)
elif selected == "My Activity":
    activity_page(session_factory, current_user.id)
elif selected == "Profile":
    profile_page(session_factory, current_user.id)
