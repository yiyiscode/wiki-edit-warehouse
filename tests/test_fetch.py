"""fetch_hour 的單元測試:用假的 session,不連網路。回應內容皆為 synthetic。"""
from datetime import datetime, timezone

import pytest

from ingest.fetch import MAX_RETRIES, fetch_hour, make_session

HOUR = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)


class FakeResp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, params, timeout):
        self.calls.append((url, params))
        return self.responses.pop(0)


def page(rcids, cont=None):
    body = {"query": {"recentchanges": [{"rcid": i} for i in rcids]}}
    if cont:
        body["continue"] = {"rccontinue": cont, "continue": "-||"}
    return FakeResp(body=body)


def run(responses):
    session, sleeps = FakeSession(responses), []
    rows = list(fetch_hour(session, HOUR, sleep=sleeps.append))
    return rows, session, sleeps


def test_follows_continue_until_exhausted():
    rows, session, _ = run([page([1, 2], cont="a|2"), page([3], cont="b|3"), page([4])])
    assert [r["rcid"] for r in rows] == [1, 2, 3, 4]
    assert [c[1].get("rccontinue") for c in session.calls] == [None, "a|2", "b|3"]


def test_window_is_half_open_hour():
    _, session, _ = run([page([])])
    url, params = session.calls[0]
    assert url == "https://zh.wikipedia.org/w/api.php"
    assert params["rcstart"] == "2026-11-10T12:00:00Z"
    assert params["rcend"] == "2026-11-10T12:59:59Z"  # 不含 13:00:00
    assert params["rcdir"] == "newer"


def test_429_waits_retry_after_then_retries_same_request():
    rows, session, sleeps = run([FakeResp(429, headers={"Retry-After": "26"}), page([1])])
    assert [r["rcid"] for r in rows] == [1]
    assert sleeps == [26.0]
    assert session.calls[0] == session.calls[1]


def test_ratelimited_error_in_200_body_is_retried():
    rows, _, sleeps = run([FakeResp(body={"error": {"code": "ratelimited"}}), page([1])])
    assert [r["rcid"] for r in rows] == [1]
    assert sleeps == [5.0]  # 沒有 Retry-After 時的退避起點


def test_other_api_error_raises_without_retry():
    with pytest.raises(RuntimeError, match="badvalue"):
        run([FakeResp(body={"error": {"code": "badvalue"}})])


def test_gives_up_after_max_retries():
    with pytest.raises(RuntimeError, match="重試"):
        run([FakeResp(429, headers={"Retry-After": "1"})] * MAX_RETRIES)


def test_rejects_non_hour_or_naive_start():
    with pytest.raises(ValueError):
        next(fetch_hour(FakeSession([]), HOUR.replace(minute=30)))
    with pytest.raises(ValueError):
        next(fetch_hour(FakeSession([]), HOUR.replace(tzinfo=None)))


def test_session_requires_user_agent(monkeypatch):
    monkeypatch.delenv("WIKI_USER_AGENT", raising=False)
    with pytest.raises(RuntimeError):
        make_session()
    assert make_session("x/0.1 (https://example.org)").headers["User-Agent"].startswith("x/0.1")
