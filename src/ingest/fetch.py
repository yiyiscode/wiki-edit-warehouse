"""從 MediaWiki Action API 抓一個小時窗的 recentchanges(SPEC 第 6.1、8 節)。"""
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

import requests

# comment、tags 不在 SPEC 的欄位清單內,但來源 30 天後就取不回,先收進 raw
RCPROP = "title|ids|sizes|flags|user|userid|timestamp|loginfo|comment|tags"
RETRY_CODES = {"ratelimited", "maxlag"}  # HTTP 200 但 body 帶 error 的可重試情況
MAX_RETRIES = 8


def make_session(user_agent: str | None = None) -> requests.Session:
    """User-Agent 必須含聯絡方式,否則 Wikimedia 限速 10 次/分(查證 2026-11-12)。"""
    user_agent = user_agent or os.environ.get("WIKI_USER_AGENT")
    if not user_agent:
        raise RuntimeError("請設定 WIKI_USER_AGENT(見 .env.example)")
    session = requests.Session()
    session.headers["User-Agent"] = user_agent
    return session


def _ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(session, url: str, params: dict, sleep: Callable[[float], None]) -> dict:
    """單次請求;429/503 與 ratelimited/maxlag 依 Retry-After 等待後重試。"""
    for attempt in range(MAX_RETRIES):
        resp = session.get(url, params=params, timeout=60)
        body = None
        if resp.status_code not in (429, 503):
            resp.raise_for_status()
            body = resp.json()
            if "error" not in body:
                return body
            if body["error"].get("code") not in RETRY_CODES:
                raise RuntimeError(f"API error: {body['error']}")
        # 沒有 Retry-After 時至少等 5 秒並指數退避(Rate limits 頁的建議)
        wait = float(resp.headers.get("Retry-After") or 5 * 2**attempt)
        print(f"  retry {attempt + 1}/{MAX_RETRIES}: HTTP {resp.status_code}, wait {wait:.0f}s", flush=True)
        sleep(wait)
    raise RuntimeError(f"重試 {MAX_RETRIES} 次仍失敗: {params}")


def fetch_hour(
    session,
    hour_start: datetime,
    *,
    domain: str = "zh.wikipedia.org",
    pause: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[dict]:
    """逐頁產出時間窗 [hour_start, hour_start + 1h) 的所有紀錄,由舊到新。

    hour_start 必須是帶時區的整點。請求一次一個(serial),頁與頁之間停 pause 秒。
    """
    if hour_start.tzinfo is None or hour_start != hour_start.replace(minute=0, second=0, microsecond=0):
        raise ValueError("hour_start 必須是帶時區的整點")
    params = {
        "action": "query",
        "list": "recentchanges",
        "format": "json",
        "formatversion": "2",
        "maxlag": "5",
        "rcdir": "newer",
        "rcstart": _ts(hour_start),
        # rcend 含端點,時間戳精度為秒,所以取 H+1 的前一秒
        "rcend": _ts(hour_start + timedelta(hours=1) - timedelta(seconds=1)),
        "rclimit": "500",
        "rcprop": RCPROP,
    }
    url = f"https://{domain}/w/api.php"
    cont: dict = {}
    while True:
        body = _get(session, url, {**params, **cont}, sleep)
        yield from body["query"]["recentchanges"]
        cont = body.get("continue") or {}
        if not cont:
            return
        sleep(pause)
