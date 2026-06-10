import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.main as main_module

@pytest.fixture(autouse=True)
def reset_state():
    main_module.login_state["status"] = "idle"
    yield

def test_login_status_no_session(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    try:
        client = TestClient(main_module.app)

        response = client.get("/login/status")
        assert response.status_code == 200
        assert response.json() == {"logged_in": False, "pending": False}
    finally:
        main_module.SESSION_DIR = original


def test_login_status_with_verified_session_flag(tmp_path):
    original = main_module.SESSION_DIR
    session_dir = tmp_path / "facebook"
    session_dir.mkdir()
    (session_dir / "logged_in.flag").write_text("true")

    main_module.SESSION_DIR = str(session_dir)
    try:
        client = TestClient(main_module.app)

        response = client.get("/login/status")
        assert response.status_code == 200
        assert response.json()["logged_in"] is True
    finally:
        main_module.SESSION_DIR = original


def test_login_status_pending(tmp_path):
    original = main_module.SESSION_DIR
    main_module.SESSION_DIR = str(tmp_path / "facebook")
    main_module.login_state["status"] = "pending"
    try:
        client = TestClient(main_module.app)

        response = client.get("/login/status")
        assert response.status_code == 200
        data = response.json()
        assert data["logged_in"] is False
        assert data["pending"] is True
    finally:
        main_module.SESSION_DIR = original


class FakePage:
    def __init__(self, url, locators):
        self.url = url
        self.viewport_size = {"width": 1200, "height": 800}
        self._locators = locators

    def locator(self, selector):
        return FakeLocator(self._locators.get(selector, []))


class FakeLocator:
    def __init__(self, items):
        self.items = items

    def count(self):
        return len(self.items)

    def nth(self, index):
        return self.items[index]


class FakeControl:
    def __init__(self, box, visible=True, aria_label="", text=""):
        self.box = box
        self.visible = visible
        self.attrs = {"aria-label": aria_label}
        self.text = text

    def is_visible(self, timeout=None):
        return self.visible

    def get_attribute(self, name, timeout=None):
        return self.attrs.get(name)

    def inner_text(self, timeout=None):
        return self.text

    def bounding_box(self, timeout=None):
        return self.box


def test_messenger_ready_controls_require_lower_textbox_and_send_button():
    page = FakePage(
        "https://www.facebook.com/messages/t/123",
        {
            'div[role="textbox"]': [
                FakeControl({"x": 300, "y": 650, "width": 500, "height": 40}, aria_label="Message")
            ],
            'div[contenteditable="true"]': [],
            'div[aria-label="Send"][role="button"]': [
                FakeControl({"x": 850, "y": 650, "width": 40, "height": 40}, aria_label="Send")
            ],
            'div[aria-label*="Send"][role="button"]': [],
            'button[aria-label="Send"]': [],
            'button[aria-label*="Send"]': [],
        },
    )

    assert main_module._page_has_messenger_ready_controls(page) is True


def test_messenger_ready_controls_reject_search_box_without_send_button():
    page = FakePage(
        "https://www.facebook.com/messages",
        {
            'div[role="textbox"]': [
                FakeControl({"x": 20, "y": 80, "width": 300, "height": 40}, aria_label="Search Messenger")
            ],
            'div[contenteditable="true"]': [],
            'div[aria-label="Send"][role="button"]': [],
            'div[aria-label*="Send"][role="button"]': [],
            'button[aria-label="Send"]': [],
            'button[aria-label*="Send"]': [],
        },
    )

    assert main_module._page_has_messenger_ready_controls(page) is False
