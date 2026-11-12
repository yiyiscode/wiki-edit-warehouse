# RESUME

更新:2026-11-12

## 目前進度
- `docs/SPEC.md` v0.2 定案(資料集:zhwiki recentchanges API)。
- **M1 進行中**,AI 負責的部分已完成,在 `feat/spec` 分支:
  - `docker-compose.yml`(Postgres 16)、`sql/001_raw.sql`(`raw.raw_recentchange`)。
  - `src/ingest/fetch.py`:分頁、429/503 與 `ratelimited`/`maxlag` 重試、User-Agent。`tests/test_fetch.py` 8 個測試通過。
  - `src/ingest/backfill.py`:`fetch`(API → `data/landing/` 的 gzip 落地檔,可中斷續跑)、`load`(落地檔 → raw)。
  - `src/ingest/load_raw.py`:只有介面;`tests/test_load_raw.py` 9 個契約測試,目前全部失敗(預期)。
  - CI:`.github/workflows/ci.yml`(repo 尚未推上 GitHub,未實際跑過)。
- 真實 API 試抓 2026-11-12 12 時:1,709 筆、`rcid` 無重複、沒遇到 429。
- M1 的兩個確認事項已寫回 SPEC:限速(第 5 節)、未登入編輯(第 7.2 節)。

## 下一步
1. ~~建 GitHub repo~~ 完成(2026-11-12):https://github.com/yiyiscode/wiki-edit-warehouse ,公開,目前只有 `feat/spec` 分支(也是預設分支,還沒有 `main`)。
2. **回補的擷取已完成(2026-11-12)**:720 個小時、998,739 列、41.5 MB,`rcid` 無重複、小時無缺口、0 次 429。第一個小時(10-13 14 時)不完整,最早一筆是 14:39:34。有 31 個小時低於 300 筆,DQ 量異常門檻 M3 要調。之後要補新的小時,重跑同一指令即可:
   `set -a; . ./.env; set +a; PYTHONPATH=src .venv/Scripts/python -m ingest.backfill fetch`
   估計 720 小時、約 3,000–4,500 次請求,一到兩小時。
3. **使用者手寫** `load_raw`,讓 `pytest tests/test_load_raw.py` 全過;AI 審查並挑戰。
4. `python -m ingest.backfill load`,連跑兩次確認筆數不變 → M1 驗收。
5. M1 驗收現況:「連續回補至少 3 天」已達成(30 天);「所有 429 都重試成功」因為全程 0 次 429,重試路徑只有單元測試驗過,沒有實地驗證。只差步驟 3、4。

## 環境
- `docker compose up -d` 起 Postgres(`postgresql://wew:wew@localhost:5432/wew`)。
- Python 用 `.venv`;測試:`.venv/Scripts/python -m pytest -q`。
- Docker Desktop 裝在 `%LOCALAPPDATA%\Programs\DockerDesktop`,要先開。

## 關鍵決策
- 現行規格:`docs/SPEC.md` v0.2。
- 為什麼換資料集、實測數字、替代方案:`docs/adr/0001-dataset-wikipedia-recentchanges.md`。
- 白話版與選擇題:`docs/overview.html`(尚未反映落地檔這一層)。
- 落地檔列為正式的一層(使用者 2026-11-12 決定):`docs/adr/0002-landing-files-before-raw.md`。
- User-Agent 聯絡方式用 repo 網址(使用者 2026-11-12 再次確認);已填入 `.env`。
- 2026-11-12 推上 GitHub 前改寫過歷史:移除 `de-skill-priority-2026-11-06.md`(本機保留、已列入 `.gitignore`),commit 信箱改為 GitHub noreply(只設在這個 repo 的 git config)。舊的 commit 雜湊已失效。

## 設計者自行補上、使用者未逐項表態的細節
不同意請直接改 SPEC:
- 第四張維度表由「事件種類」改為 `dim_wiki`;編輯種類(`edit`/`new`)改成 `fact_edit` 上的欄位。
- 所有未登入編輯共用 `dim_user` 的一列「匿名」。來源實際用臨時帳號表示,是否改成各自一列留到 M2(SPEC 第 14 節)。
- 不支援對較早的日子亂序重跑;需要時清空 warehouse 層,從 raw 依日序重播。
- User-Agent 的聯絡方式用 repo 網址,不放個人 email。
- 專案代號暫定 `wiki-edit-warehouse`。
- (M1 新增)`rcprop` 多收了 `comment`、`tags`:不在 SPEC 欄位清單,但過了 30 天取不回。
- (M1 新增)`raw_recentchange` 多一個 `rc_timestamp` 欄位(取自 payload),供 staging 以小時切分。
