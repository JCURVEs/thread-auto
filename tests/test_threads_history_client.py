"""Tests for Threads API history client."""

from threads_history_client import (
    DEFAULT_THREAD_FIELDS,
    fetch_conversation_page,
    fetch_threads_page,
    iter_thread_conversation,
    iter_user_threads,
)


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = "fake"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def get(self, url, params, headers, timeout):
        self.calls.append({
            "url": url,
            "params": params,
            "headers": headers,
            "timeout": timeout,
        })
        return FakeResponse(self.payloads.pop(0))


def test_fetch_threads_page_sends_auth_header_and_params():
    session = FakeSession([{"data": []}])

    payload = fetch_threads_page(
        access_token="token",
        since="2026-01-01",
        limit=25,
        session=session,
    )

    assert payload == {"data": []}
    call = session.calls[0]
    assert call["url"].endswith("/me/threads")
    assert call["headers"]["Authorization"] == "Bearer token"
    assert call["params"]["since"] == "2026-01-01"
    assert call["params"]["limit"] == 25
    assert "media_url" in DEFAULT_THREAD_FIELDS
    assert "thumbnail_url" in DEFAULT_THREAD_FIELDS
    assert "children" in DEFAULT_THREAD_FIELDS


def test_iter_user_threads_follows_after_cursor():
    session = FakeSession([
        {
            "data": [{"id": "1"}],
            "paging": {"cursors": {"after": "cursor-1"}},
        },
        {
            "data": [{"id": "2"}],
            "paging": {"cursors": {}},
        },
    ])

    posts = list(iter_user_threads("token", session=session))

    assert [post["id"] for post in posts] == ["1", "2"]
    assert session.calls[1]["params"]["after"] == "cursor-1"


def test_fetch_conversation_page_uses_thread_id_endpoint():
    session = FakeSession([{"data": []}])

    fetch_conversation_page("root-1", "token", session=session)

    call = session.calls[0]
    assert call["url"].endswith("/root-1/conversation")
    assert call["params"]["reverse"] == "false"
    assert call["headers"]["Authorization"] == "Bearer token"


def test_iter_thread_conversation_follows_after_cursor():
    session = FakeSession([
        {
            "data": [{"id": "root-1"}, {"id": "reply-1"}],
            "paging": {"cursors": {"after": "cursor-1"}},
        },
        {
            "data": [{"id": "reply-2"}],
            "paging": {"cursors": {}},
        },
    ])

    posts = list(iter_thread_conversation("root-1", "token", session=session))

    assert [post["id"] for post in posts] == ["root-1", "reply-1", "reply-2"]
    assert session.calls[1]["params"]["after"] == "cursor-1"
