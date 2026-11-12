"""raw 冪等載入 —— 由使用者手寫(SPEC 第 11 節)。介面與測試由 AI 提供。"""
from typing import Iterable

import psycopg


def load_raw(conn: psycopg.Connection, wiki: str, records: Iterable[dict]) -> int:
    """把 API 原始紀錄寫入 raw.raw_recentchange,回傳「這次實際新增」的筆數。

    契約(tests/test_load_raw.py 逐條驗證):
    - (wiki, rcid) 已存在就略過,不覆寫既有列(payload、loaded_at 都不變)。
    - payload 原樣存成 JSONB;rc_timestamp 取自 record["timestamp"]。
    - 不 commit、不 rollback:交易邊界由呼叫端決定。
    - records 可能是 generator,只能走訪一次;一個小時約 1,000–3,000 筆。
    """
    raise NotImplementedError("TODO(使用者手寫):raw 冪等載入")
