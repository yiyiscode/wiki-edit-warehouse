"""M1 回補(Airflow 在 M4 接手排程)。

  python -m ingest.backfill fetch [--days 30]   API -> data/landing/<wiki>/<小時>.jsonl.gz
  python -m ingest.backfill load                落地檔 -> raw.raw_recentchange

落地檔存在即代表該小時已抓完,所以 fetch 中斷後重跑會自動接續。
load 每次重讀全部落地檔,靠 load_raw 的冪等保證不重複。
"""
import argparse
import gzip
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ingest.fetch import fetch_hour, make_session

LANDING = Path("data/landing")
DOMAINS = {"zhwiki": "zh.wikipedia.org"}


def fetch(wiki: str, days: int) -> None:
    session = make_session()
    out_dir = LANDING / wiki
    out_dir.mkdir(parents=True, exist_ok=True)
    # 只抓已結束的小時;由舊到新,先救快過期的
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hour = end - timedelta(days=days)
    while hour < end:
        path = out_dir / f"{hour:%Y-%m-%dT%H}.jsonl.gz"
        if not path.exists():
            records = list(fetch_hour(session, hour, domain=DOMAINS[wiki]))
            if records:
                tmp = path.with_suffix(".tmp")
                with gzip.open(tmp, "wt", encoding="utf-8") as f:
                    for r in records:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                os.replace(tmp, path)  # 寫完才改名,中斷不會留下半個檔
            # 0 筆不落檔:可能已超過來源 30 天保留期,也可能是暫時異常,下次重試
            print(f"{hour:%Y-%m-%d %H}h  {len(records):>5} rows", flush=True)
        hour += timedelta(hours=1)


def load(wiki: str) -> None:
    import psycopg

    from ingest.load_raw import load_raw

    url = os.environ.get("DATABASE_URL", "postgresql://wew:wew@localhost:5432/wew")
    with psycopg.connect(url) as conn:
        for path in sorted((LANDING / wiki).glob("*.jsonl.gz")):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                inserted = load_raw(conn, wiki, (json.loads(line) for line in f))
            conn.commit()  # 一個小時一個交易
            print(f"{path.name}  +{inserted}", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["fetch", "load"])
    p.add_argument("--wiki", default="zhwiki", choices=DOMAINS)
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args()
    fetch(args.wiki, args.days) if args.command == "fetch" else load(args.wiki)
