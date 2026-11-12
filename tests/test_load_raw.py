"""load_raw 的契約測試。使用者實作前全部失敗(NotImplementedError)。

需要 Postgres:docker compose up -d。每個測試在交易內執行,結束即 rollback,不留資料。
測試資料皆為 synthetic(wiki 用 'testwiki',rcid 為虛構)。
"""
import os
from pathlib import Path

import psycopg
import pytest

from ingest.load_raw import load_raw

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://wew:wew@localhost:5432/wew")
DDL = Path(__file__).parents[1] / "sql" / "001_raw.sql"
WIKI = "testwiki"


def synthetic(rcid: int, **extra) -> dict:
    """synthetic:形狀比照 2026-11-12 實測的 zhwiki 紀錄,內容為虛構。"""
    return {
        "type": "edit", "ns": 0, "title": f"合成頁面{rcid}", "pageid": 1000 + rcid,
        "revid": 5000 + rcid, "old_revid": 4000 + rcid, "rcid": rcid,
        "user": "SyntheticUser", "userid": 42, "bot": False, "new": False, "minor": False,
        "oldlen": 100, "newlen": 120, "timestamp": f"2026-11-10T12:00:{rcid % 60:02d}Z",
        "comment": "synthetic", "tags": [], **extra,
    }


@pytest.fixture
def conn():
    try:
        c = psycopg.connect(DATABASE_URL, connect_timeout=5)
    except psycopg.OperationalError as e:
        pytest.fail(f"連不上 Postgres,先執行 docker compose up -d({e})")
    c.execute(DDL.read_text(encoding="utf-8"))
    yield c
    c.rollback()
    c.close()


def count(conn) -> int:
    return conn.execute(
        "SELECT count(*) FROM raw.raw_recentchange WHERE wiki = %s", (WIKI,)
    ).fetchone()[0]


def test_first_load_inserts_all(conn):
    assert load_raw(conn, WIKI, [synthetic(1), synthetic(2), synthetic(3)]) == 3
    assert count(conn) == 3


def test_same_batch_twice_changes_nothing(conn):
    """M1 驗收:同一小時載入兩次,筆數不變。"""
    batch = [synthetic(1), synthetic(2), synthetic(3)]
    load_raw(conn, WIKI, batch)
    assert load_raw(conn, WIKI, batch) == 0
    assert count(conn) == 3


def test_overlapping_batch_inserts_only_new(conn):
    load_raw(conn, WIKI, [synthetic(1), synthetic(2)])
    assert load_raw(conn, WIKI, [synthetic(2), synthetic(3)]) == 1
    assert count(conn) == 3


def test_duplicate_rcid_within_one_batch(conn):
    assert load_raw(conn, WIKI, [synthetic(1), synthetic(1)]) == 1
    assert count(conn) == 1


def test_conflict_does_not_overwrite_existing_row(conn):
    load_raw(conn, WIKI, [synthetic(1)])
    load_raw(conn, WIKI, [synthetic(1, title="被改過的標題")])
    title = conn.execute(
        "SELECT payload->>'title' FROM raw.raw_recentchange WHERE wiki = %s AND rcid = 1", (WIKI,)
    ).fetchone()[0]
    assert title == "合成頁面1"


def test_same_rcid_on_another_wiki_is_a_different_row(conn):
    load_raw(conn, WIKI, [synthetic(1)])
    assert load_raw(conn, "testwiki2", [synthetic(1)]) == 1


def test_payload_stored_verbatim_and_timestamp_extracted(conn):
    record = synthetic(7, type="log", logtype="move",
                       logparams={"target_ns": 118, "target_title": "Draft:合成頁面7"})
    load_raw(conn, WIKI, [record])
    payload, ts = conn.execute(
        "SELECT payload, rc_timestamp AT TIME ZONE 'UTC' FROM raw.raw_recentchange"
        " WHERE wiki = %s AND rcid = 7", (WIKI,)
    ).fetchone()
    assert payload == record
    assert ts.isoformat() == "2026-11-10T12:00:07"


def test_accepts_generator_and_empty_input(conn):
    assert load_raw(conn, WIKI, (synthetic(i) for i in range(1, 4))) == 3
    assert load_raw(conn, WIKI, []) == 0


def test_does_not_commit(conn):
    load_raw(conn, WIKI, [synthetic(1)])
    conn.rollback()
    assert count(conn) == 0
