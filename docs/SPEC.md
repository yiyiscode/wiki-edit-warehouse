# SPEC:GitHub 趨勢資料倉儲(gh-trend-warehouse)

- 版本:v0.1(2026-11-11)
- 狀態:設計定案、尚未實作。本文件描述的是「要做成什麼樣」,不是現有系統的行為。
- 決策來源:2026-11-06 至 2026-11-07 的設計討論(grilling)。白話版與 Why 說明見 [`overview.html`](overview.html)。
- 本文件是目標、範圍、驗收條件的單一事實來源;其他文件與本文件衝突時,以本文件為準並回頭修正。

---

## 1. 背景

| 項目 | 內容 |
|---|---|
| 使用者 | 以資料工程師(DE)職缺為主、AI 工程師為輔;碩士畢業;約 3 年 Python、MySQL、ML 與資料分析經驗;做過一個本機的職缺爬蟲專案 |
| 履歷缺口 | 缺少資料倉儲、資料治理等 DE 核心經驗 |
| 缺口證據 | [`de-skill-priority-2026-11-06.md`](../de-skill-priority-2026-11-06.md) 第 5.1 節:62 筆有全文的深評 DE 職缺中,ETL 61%、資料治理/品質 32%、資料倉儲 27%、Airflow 27%、PostgreSQL 24%;資料治理、資料倉儲、PostgreSQL、Airflow 在使用者履歷為「無」。註:這些筆數是該報告作者自行查詢,未經 fact-checker 重現(報告第 5.5、9 節) |

### 與 2026-11-06 優先度報告的差異

該報告第 6 節推薦用 Job Finder 本機資料做 Job Market Warehouse。設計討論中使用者選了 GH Archive。理由:

1. 職缺資料只保留最新一版,SCD2 歷史只能從開始載入那天累積(報告第 6 節自己也指出這點);GH Archive 可回補 30 天。
2. 使用者要求資料來源能在雲端順利存取。
3. (設計者判斷)GH Archive 每小時都有新資料,可當 Airflow 的真實增量來源;職缺資料量小,用來展示分區與回補較弱。

代價:失去「資料是自己的、故事連貫」的優勢,且題材與求職領域無直接關聯。

---

## 2. 目的(Why)

| # | 目的 | 怎麼算達成 |
|---|---|---|
| P1 | 透過實作真正理解 DE 核心概念,包含何時、為何使用 NoSQL | 使用者能不看文件解釋第 3 節每個目標的設計理由與替代方案 |
| P2 | 專案深度足以讓面試被深入追問而不露餡 | `docs/interview/` 的追問清單(M5 產出)每題都對應到 repo 內可指出的程式碼、測試或 ADR |
| P3 | 練習與 AI 協作:使用者負責需求、架構決策與驗收;AI 負責實作並挑戰使用者的設計 | 每項架構決策都有 ADR,記錄使用者的選擇與 AI 提出的替代方案 |
| P4 | 需要親手寫過才能理解的概念由使用者手打;重複性、樣板性實作由 AI 負責 | 第 9 節「手寫清單」的程式碼由使用者撰寫(commit 可追溯) |

---

## 3. 目標(What),依優先度

| # | 能力 | 本專案要做出的東西 | 完成標準 |
|---|---|---|---|
| G1 | 資料倉儲建模:星狀模型、事實/維度表、SCD | 2 張事實表 + 4 張維度表(第 7 節);`dim_repo` 為 SCD2、`dim_actor` 為 SCD1 | 能以 SQL 回答「某專案某天屬於哪個語言」且結果符合 SCD2 版本;能解釋事件型與快照型事實表、半可加度量 |
| G2 | 資料治理與品質 | 手寫 DQ 規則、`dq_results` 表、失敗阻擋下游;欄位血緣與資料字典 | 注入壞資料時,檢查會攔下、記錄原因、下游不執行 |
| G3 | PostgreSQL,並理解與 NoSQL 的取捨 | raw 層以 JSONB 存原始事件;ADR 比較 JSONB 與 MongoDB | ADR 附實測查詢與結論,寫明何時該改用 MongoDB |
| G4 | ETL 深度:冪等、增量與全量、失敗重跑 | 小時分區增量載入、30 天回補、重跑不重複 | 同一小時連跑多次,所有表的筆數與內容不變(自動化測試) |
| G5 | Airflow 排程編排 | 每小時 ingest DAG、每日轉換/快照/SCD2/DQ DAG | catchup 能補完回補區間;任務失敗後重跑結果正確 |
| G6 | Docker、雲端、K8s、MLOps 概念 | Docker Compose(實作)、免費雲端 Postgres(實作)、K8s manifest 與 MLOps 設計文件(標示「設計、未實作」) | 全環境一個指令啟動;雲端倉儲可連線查詢;設計文件標示清楚 |

---

## 4. 範圍外(本版不做)

以下為設計者的範圍界定,使用者未逐項表態;要納入任何一項請改這節。

- Spark、Kafka、串流處理
- 追蹤所有出現過的 repo(只追 Top 2000,見第 6 節)
- K8s 實際部署、MLOps 實作(M5 完成後再評估)
- RAG / LLM 應用
- 生產級高可用、權限管理

---

## 5. 限制

| 限制 | 來源 |
|---|---|
| 資料來源需在雲端穩定存取,無反爬蟲或 IP 封鎖 | 使用者需求 |
| 免費或低成本 | 使用者需求 |
| 雲端儲存:Neon Free 1 GB/專案(閒置 5 分鐘 suspend);Supabase Free 500 MB(閒置 1 週暫停) | 官方方案頁,查證於 2026-11-07 |
| GitHub API:PAT 5000 次/小時;未驗證 60 次/小時 | docs.github.com,查證於 2026-11-07 |
| 環境:Windows 10;Docker 29.7.2、Docker Compose v5.5.0 | 本機 `docker --version` 實測,2026-11-11 |

---

## 6. 資料來源

### 6.1 GH Archive(事件)

- 網址:`https://data.gharchive.org/YYYY-MM-DD-H.json.gz`,小時不補零。
- 實測(2026-10-20 樣本,查證於 2026-11-07):單一小時檔約 10–13 MB(壓縮),12 時一檔 58,084 筆事件。全天量與是否限速未證實。
- 頂層 `repo` 只有 `id`、`name`、`url`,不含 language、description。
- 範圍:回補 30 天,之後每小時增量。

### 6.2 GitHub REST API(repo 屬性)

- `GET /repos/{owner}/{repo}`,每日一次。
- 追蹤對象:前一日事件活躍度 Top 2000 的 repo(每日 2000 次請求,低於額度)。
- SCD2 追蹤欄位:`full_name`、`language`、`description`、`topics`、`archived`、`license.spdx_id`、`owner.login`。
- `stargazers_count`、`forks_count`、`open_issues_count` 是度量,進 `fact_repo_daily`,不觸發 SCD2。

---

## 7. 架構與資料模型

架構圖:[`svg/arch.svg`](svg/arch.svg);星狀模型圖:[`svg/star.svg`](svg/star.svg)。

| 層 | 位置 | 內容 |
|---|---|---|
| raw | 本機 Postgres | `raw_event`(JSONB,以 `event_id` 為唯一鍵)、`raw_repo_snapshot`(JSONB,每日一份) |
| staging | 本機 Postgres | 型別化、去重、bot 標記;DQ 在此把關 |
| warehouse | 雲端 Postgres | 事實表、維度表、`dq_results` |

### 7.1 事實表

| 表 | 粒度 | 主要欄位 | 備註 |
|---|---|---|---|
| `fact_event` | 一筆 GH 事件 | `event_id`、`repo_sk`、`actor_sk`、`date_key`、`event_type_key`、`event_hour`、`is_backdated` | 可加總;以小時分區載入 |
| `fact_repo_daily` | 一個 repo × 一天 | `repo_sk`、`date_key`、`stargazers_count`、`forks_count`、`open_issues_count` | 半可加:可跨 repo 加總,不可跨日加總 |

### 7.2 維度表

| 表 | 類型 | 主要欄位 |
|---|---|---|
| `dim_repo` | SCD2 | `repo_sk`、`repo_id`、第 6.2 節追蹤欄位、`valid_from`、`valid_to`、`is_current` |
| `dim_actor` | SCD1 | `actor_sk`、`actor_id`、`login`、`is_bot` |
| `dim_date` | 靜態 | `date_key`、日期、週幾、週次、月份 |
| `dim_event_type` | 靜態 | `event_type_key`、事件名稱、類別 |

### 7.3 早於首次快照的事件

回補事件發生時沒有 repo 快照。`dim_repo` 每個 repo 的第一版 `valid_from` 設為開放起點(Postgres `-infinity`),舊事件連到這一版,`fact_event.is_backdated = true`,文件註明「屬性為近似」。

---

## 8. ETL 規則

| 主題 | 規則 |
|---|---|
| 冪等(raw) | `event_id` 衝突即略過(`ON CONFLICT DO NOTHING`) |
| 冪等(fact) | 以小時分區為單位,在單一交易內 delete 該分區後 insert;失敗整段 rollback |
| SCD2 | 名片欄位雜湊不同才關閉舊版(填 `valid_to`、`is_current=false`)並新增一版;相同則不動 |
| SCD1 | `login` 變更直接覆寫 |
| 增量 / 全量 | 事件為小時增量;維度與 `fact_repo_daily` 為每日增量;支援指定區間重跑 |
| 回補 | 由 Airflow catchup 處理 30 天區間 |
| 轉換層 | 先純 SQL(由 Airflow 呼叫);M6 用 dbt snapshot 重做 `dim_repo` 對照 |

## 9. 資料品質與治理

| 規則類型 | 範例 |
|---|---|
| 非空 | `event_id`、`repo_id`、`created_at` 不可為空 |
| 唯一 | `fact_event.event_id` 唯一;`dim_repo` 每個 `repo_id` 恰一列 `is_current=true` |
| 參照完整性 | `fact_event.repo_sk` 都能在 `dim_repo` 找到 |
| 新鮮度 | 最新事件時間距今不超過設定門檻 |
| 筆數對帳 | raw 該小時筆數 = staging 去重後筆數 + 被剔除筆數 |

結果寫入 `dq_results`(規則、分區、通過與否、實際值、執行時間);任一阻擋級規則失敗,下游任務不執行。另交付欄位血緣與資料字典文件。

## 10. 排程

| DAG | 頻率 | 步驟 |
|---|---|---|
| `ingest_hourly` | 每小時 | 下載該小時檔 → raw → staging → `fact_event` |
| `transform_daily` | 每日 | API 快照 → `dim_repo`(SCD2)→ `fact_repo_daily` → DQ |

---

## 11. 分工(手寫清單)

| 由使用者手寫 | 由 AI 實作 |
|---|---|
| SCD2 merge SQL | Docker Compose、環境設定 |
| 冪等載入(raw 略過、fact 分區覆寫) | Airflow DAG 骨架 |
| 資料品質檢查 | 下載、解壓、JSON 解析 |
| | 測試資料、CI、文件草稿 |

手寫項目的流程:AI 先給介面與會失敗的測試,使用者實作,AI 審查並挑戰。

## 12. 里程碑與驗收

| 里程碑 | 內容 | 驗收條件 |
|---|---|---|
| M1 | Compose + raw 冪等載入 | 同一小時檔載入兩次,`raw_event` 筆數不變;小規模下載試跑確認無限速問題 |
| M2 | 星狀模型 + SCD2 | 合成變更資料(標示 synthetic)通過 SCD2 測試;`is_backdated` 正確標記 |
| M3 | DQ | 每類規則各有一個注入壞資料的測試,皆被攔下並寫入 `dq_results` |
| M4 | Airflow | 兩個 DAG 跑完一段回補區間;任務失敗後重跑結果與一次跑完相同 |
| M5 | 雲端 + 文件 | 倉儲層部署至免費雲端 Postgres;README(英文)、ADR、資料字典、血緣、面試追問清單、K8s manifest、MLOps 設計文件 |
| M6 | dbt 對照 | 以 dbt snapshot 重建 `dim_repo`,與手寫版比較的結果寫成文件 |

每個里程碑完成即 commit 到功能分支,並更新 `RESUME.md`。CI(GitHub Actions)在每次 push 跑 pytest。

---

## 13. 誠實揭露

| 限制 | 對外說法 |
|---|---|
| SCD2 真實變化少 | 真實資料靠每日快照累積;邏輯正確性由合成資料測試驗證 |
| 回補事件屬性為近似 | `is_backdated` 標記並寫明限制 |
| GH Archive 限速未證實 | M1 先小規模試下載 |
| K8s、MLOps 僅設計 | 履歷與 README 標示「設計、未實作」 |
| 免費額度可能變動 | 數字附查證日期,部署前再確認 |

## 14. 未決問題

| 問題 | 何時決定 |
|---|---|
| 雲端選 Neon(1 GB)或 Supabase(500 MB) | M5 前 |
| bot 判定規則(登入名 `[bot]` 後綴或其他) | M2 前 |
| 「活躍度 Top 2000」的計算窗口與指標 | M2 前 |
| 新鮮度門檻 | M3 前 |
| 是否做查詢展示(儀表板或 SQL 範例) | M5 前 |
