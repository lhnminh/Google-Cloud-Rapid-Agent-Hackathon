import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend.browser_agent as browser_agent


def test_send_browser_defaults_to_headless(monkeypatch):
    monkeypatch.delenv("SEND_BROWSER_HEADLESS", raising=False)

    assert browser_agent._send_browser_headless() is True


def test_send_browser_can_be_forced_headed(monkeypatch):
    monkeypatch.setenv("SEND_BROWSER_HEADLESS", "false")

    assert browser_agent._send_browser_headless() is False
