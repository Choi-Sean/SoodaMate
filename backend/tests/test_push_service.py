"""Push service: credential loading (JSON env or file path), visible failure modes, and
that a send never blocks the event loop or raises into the request that triggered it."""
import json
import logging
import threading
import uuid

import pytest

from app.config import settings
from app.services import push_service


@pytest.fixture(autouse=True)
def _reset_push_state(monkeypatch):
    monkeypatch.setattr(push_service, "_app", None)
    monkeypatch.setattr(push_service, "_init_attempted", False)
    monkeypatch.setattr(settings, "firebase_credentials_json", "")
    monkeypatch.setattr(settings, "firebase_credentials_path", "")


def test_no_credentials_means_off_and_it_says_so(caplog):
    with caplog.at_level(logging.WARNING, logger="app.services.push_service"):
        assert push_service._get_app() is None
    assert "push notifications are OFF" in caplog.text


def test_json_credentials_take_precedence_over_path(monkeypatch):
    seen = {}

    def fake_certificate(arg):
        seen["arg"] = arg
        return "cred"

    monkeypatch.setattr(push_service.credentials, "Certificate", fake_certificate)
    monkeypatch.setattr(push_service.firebase_admin, "initialize_app", lambda cred: object())
    monkeypatch.setattr(settings, "firebase_credentials_json", json.dumps({"type": "service_account", "project_id": "p"}))
    monkeypatch.setattr(settings, "firebase_credentials_path", "does/not/matter.json")
    assert push_service._get_app() is not None
    assert seen["arg"] == {"type": "service_account", "project_id": "p"}


def test_json_with_raw_newlines_in_the_key_still_loads(monkeypatch):
    seen = {}
    monkeypatch.setattr(push_service.credentials, "Certificate", lambda arg: seen.setdefault("arg", arg))
    monkeypatch.setattr(push_service.firebase_admin, "initialize_app", lambda cred: object())
    # A literal line break inside a JSON string is invalid strict JSON; pasting a key file into an
    # env var can produce exactly that.
    monkeypatch.setattr(settings, "firebase_credentials_json", '{"private_key": "-----BEGIN-----\nabc\n-----END-----"}')
    assert push_service._get_app() is not None
    assert seen["arg"]["private_key"].startswith("-----BEGIN-----")


def test_bad_credentials_are_logged_without_key_material(monkeypatch, caplog):
    monkeypatch.setattr(settings, "firebase_credentials_json", '{"private_key": "SUPER-SECRET-VALUE"')  # truncated JSON
    with caplog.at_level(logging.ERROR, logger="app.services.push_service"):
        assert push_service._get_app() is None
    assert "push notifications are OFF" in caplog.text
    assert "SUPER-SECRET-VALUE" not in caplog.text


class _FakeDb:
    def __init__(self, tokens):
        self._tokens = tokens

    async def execute(self, _stmt):
        tokens = self._tokens

        class _Result:
            def scalars(self):
                class _S:
                    def all(_self):
                        return tokens

                return _S()

        return _Result()


@pytest.mark.asyncio
async def test_send_runs_off_the_event_loop_and_survives_a_failing_token(monkeypatch, caplog):
    main_thread = threading.get_ident()
    calls = []

    def fake_send(message, app=None):
        calls.append((threading.get_ident(), message.token))
        if message.token == "bad-token":
            raise RuntimeError("Requested entity was not found.")
        return "projects/x/messages/1"

    monkeypatch.setattr(push_service, "_get_app", lambda: object())
    monkeypatch.setattr(push_service.messaging, "send", fake_send)
    with caplog.at_level(logging.WARNING, logger="app.services.push_service"):
        await push_service.send_to_user(_FakeDb(["bad-token", "good-token"]), uuid.uuid4(), "Title", "Body", {"type": "match"})

    assert [t for _, t in calls] == ["bad-token", "good-token"]  # one bad token doesn't stop the rest
    assert all(tid != main_thread for tid, _ in calls)  # blocking HTTP call never runs on the loop thread
    assert "failed (RuntimeError)" in caplog.text
    assert "bad-token" not in caplog.text  # tokens are never logged


@pytest.mark.asyncio
async def test_send_with_no_token_says_why_and_sends_nothing(monkeypatch, caplog):
    monkeypatch.setattr(push_service, "_get_app", lambda: object())
    monkeypatch.setattr(push_service.messaging, "send", lambda *a, **k: pytest.fail("must not send"))
    with caplog.at_level(logging.INFO, logger="app.services.push_service"):
        await push_service.send_to_user(_FakeDb([]), uuid.uuid4(), "Title", "Body")
    assert "no registered device token" in caplog.text
