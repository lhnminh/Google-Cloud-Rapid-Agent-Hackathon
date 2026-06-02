import os
import shutil
import tempfile
import pytest
from fastapi.testclient import TestClient

# Patch SESSION_DIR before importing main
import backend.main as main_module

@pytest.fixture(autouse=True)
def reset_state():
    main_module.login_state["status"] = "idle"
    yield

def test_login_status_no_session(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    assert response.json() == {"logged_in": False, "pending": False}

    main_module.SESSION_DIR = original


def test_login_status_with_session(tmp_path):
    original = main_module.SESSION_DIR
    session_dir = tmp_path / "facebook"
    session_dir.mkdir()
    (session_dir / "Default").mkdir()  # non-empty

    main_module.SESSION_DIR = str(session_dir)
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    assert response.json()["logged_in"] is True

    main_module.SESSION_DIR = original


def test_login_status_pending(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    main_module.login_state["status"] = "pending"
    client = TestClient(main_module.app)

    response = client.get("/login/status")
    assert response.status_code == 200
    data = response.json()
    assert data["logged_in"] is False
    assert data["pending"] is True

    main_module.SESSION_DIR = original
