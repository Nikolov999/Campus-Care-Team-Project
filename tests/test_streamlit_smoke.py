from __future__ import annotations

from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest


APP_FILE = Path(__file__).resolve().parents[1] / "streamlit_app.py"


@pytest.mark.ui
def test_authentication_screen_loads(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "campuscare-ui.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "student.ncirl.ie,ncirl.ie")

    app = AppTest.from_file(str(APP_FILE), default_timeout=15).run()

    assert not app.exception
    assert app.text_input(key="login-email").label == "NCI email"
    assert app.button(key="login-submit").label == "Log in"
    assert app.button(key="register-submit").label == "Create account"


@pytest.mark.ui
def test_user_can_register_and_reach_dashboard(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "campuscare-register.db"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    monkeypatch.setenv("ALLOWED_EMAIL_DOMAINS", "student.ncirl.ie,ncirl.ie")

    app = AppTest.from_file(str(APP_FILE), default_timeout=15).run()
    app.text_input(key="register-first-name").set_value("UI")
    app.text_input(key="register-last-name").set_value("Tester")
    app.text_input(key="register-email").set_value("ui.tester@student.ncirl.ie")
    app.text_input(key="register-course").set_value("Computing")
    app.selectbox(key="register-year").set_value("Year 2")
    app.text_input(key="register-password").set_value("Campus123")
    app.text_input(key="register-confirm").set_value("Campus123")
    app.button(key="register-submit").click().run(timeout=15)

    assert not app.exception
    assert app.session_state["user_id"] > 0
    assert app.sidebar.radio(key="_nav_widget").value == "Home"
    assert len(app.metric) == 4
