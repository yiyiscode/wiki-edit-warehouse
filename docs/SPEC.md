# SPEC:維基百科編輯資料倉儲(wiki-edit-warehouse)

- 版本:v0.2(2026-11-12)。v0.1(2026-11-11)以 GH Archive 為資料來源,已作廢。
- 狀態:設計定案、尚未實作。本文件描述的是「要做成什麼樣」,不是現有系統的行為。
- 決策來源:2026-11-06 至 2026-11-07 的設計討論,以及 2026-11-11 至 2026-11-12 的 spec 重審(grilling)。白話版見 [`overview.html`](overview.html);換資料集的理由見 [`adr/0001-dataset-wikipedia-recentchanges.md`](adr/0001-dataset-wikipedia-recentchanges.md)。
- 本文件是目標、範圍、驗收條件的單一事實來源;其他文件與本文件衝突時,以本文件為準並回頭修正。
- 專案代號 `wiki-edit-warehouse` 為設計者暫定,使用者可改。

---

## 1. 背景

| 項目 | 內容 |
|---|---|
| 使用者 | 以資料工程師(DE)職缺為主、AI 工程師為輔;碩士畢業;約 3 年 Python、MySQL、ML 與資料分析經驗;做過一個本機的職缺爬蟲專案 |
| 履歷缺口 | 缺少資料倉儲、資料治理等 DE 核心經驗 |
| 缺口證據 | [`de-skill-priority-2026-11-06.md`](../de-skill-priority-2026-11-06.md) 第 5.1 節:62 筆有全文的深評 DE 職缺中,ETL 61%、資料治理/品質 32%、資料倉儲 27%、Airflow 27%、PostgreSQL 24%;資料治理、資料倉儲、PostgreSQL、Airflow 在使用者履歷為「無」。註:這些筆數是該報告作者自行查詢,未經 fact-checker 重現(報告第 5.5、9 節) |

### 資料集的選擇經過

| 時間 | 選擇 | 結果 |
|---|---|---|
| 2026-11-06 | 優先度報告第 6 節推薦用 Job Finder 本機職缺資料 | 未採用:沒有每小時增量,資料在本機,不符合「雲端可存取」 |
| 2026-11-07 | GH Archive + GitHub API | 2026-11-11 實測發現來源已退化,作廢 |
| 2026-11-11 | **維基百科中文版的 recentchanges API** | 現行選擇 |

代價:題材與求職領域(金融業居多)無直接關聯,資料量小(第 6 節)。面試時的說法見第 13 節。

---

## 2. 目的(Why)

| # | 目的 | 怎麼算達成 |
|---|---|---|
| P1 | 透過實作真正理解 DE 核心概念,包含何時、為何使用 NoSQL | 使用者能不看文件解釋第 3 節每個目標的設計理由與替代方案 |
| P2 | 專案深度足以讓面試被深入追問而不露餡 | `docs/interview/` 的追問清單(M5 產出)每題都對應到 repo 內可指出的程式碼、測試或 ADR |
| P3 | 練習與 AI 協作:使用者負責需求、架構決策與驗收;AI 負責實作並挑戰使用者的設計 | 每項架構決策都有 ADR,記錄使用者的選擇與 AI 提出的替代方案 |
| P4 | 需要親手寫過才能理解的概念由使用者手打;重複性、樣板性實作由 AI 負責 | 第 11 節「手寫清單」的程式碼由使用者撰寫(commit 可追溯) |

---

## 3. 目標(What),依優先度

| # | 能力 | 本專案要做出的東西 | 完成標準 |
|---|---|---|---|
| G1 | 資料倉儲建模:星狀模型、事實/維度表、SCD | 2 張事實表 + 4 張維度表(第 7 節);`dim_page` 為 SCD2、`dim_user` 為 SCD1 | 第 3.1 節三題業務問題都能以 SQL 回答,且結果符合 SCD2 版本;能解釋事件型與快照型事實表、半可加度量 |
| G2 | 資料治理與品質 | 手寫 DQ 規則、`dq_results` 表、失敗阻擋下游;欄位血緣與資料字典 | 注入壞資料時,檢查會攔下、記錄原因、下游不執行 |
| G3 | PostgreSQL,並理解與 NoSQL 的取捨 | raw 層以 JSONB 存原始紀錄;ADR 比較 JSONB 與 MongoDB | ADR 附實測查詢與結論,寫明何時該改用 MongoDB |
| G4 | ETL 深度:冪等、增量與全量、失敗重跑 | 小時增量擷取、30 天回補、重跑不重複 | 同一小時、同一日連跑多次,所有表的筆數與內容不變(自動化測試) |
| G5 | Airflow 排程編排 | 每小時擷取 DAG、每日倉儲 DAG | 每小時 DAG 的 catchup 能補完回補區間;任務失敗後重跑結果正確 |
| G6 | Docker、雲端、K8s、MLOps 概念 | Docker Compose(實作)、Neon 免費 Postgres(實作)、K8s manifest 與 MLOps 設計文件(標示「設計、未實作」) | 全環境一個指令啟動;雲端倉儲可連線查詢;設計文件標示清楚 |

### 3.1 業務問題(G1 的驗收,M5 各附一個 SQL 範例)

| # | 問題 | 用到的表 | 要展示的概念 |
|---|---|---|---|
| A | 各命名空間每天的編輯次數與位元組淨增減 | `fact_edit`、`dim_page`、`dim_date` | 可加總的事實;以「編輯當時」的命名空間歸類 |
| B | 頁面改名(例如從條目退回草稿)前後 7 天的編輯量;分別用「當時的標題」與「現在的標題」計算並比較差異 | `fact_edit`、`dim_page` | SCD2 的價值:不留歷史會算錯 |
| D | 每週位元組成長最多的頁面 | `fact_page_daily`、`dim_page`、`dim_date` | 半可加度量:頁面大小不可跨日加總,要用期末減期初 |

候選 C(機器人、登入者、匿名者的編輯占比)未選入驗收;資料模型支援,有餘力再做。

---

## 4. 範圍外(本版不做)

- Spark、Kafka、串流處理(含 Wikimedia EventStreams)
- 頁面保護狀態的追蹤:保護到期時來源不產生事件,只靠事件流會追錯(見第 7.3 節)
- 使用者權限群組的歷史(`rights` 日誌)
- 英文版等其他語言版本:M5 前再評估(第 14 節)
- 分類變動(`categorize`)與 `move` 以外的管理日誌:只留在 raw / staging,不進事實表
- 儀表板:展示只用 SQL 範例
- K8s 實際部署、MLOps 實作(M5 完成後再評估)
- RAG / LLM 應用
- 生產級高可用、權限管理

---

## 5. 限制

| 限制 | 來源 |
|---|---|
| 資料來源需在雲端穩定存取,無反爬蟲或 IP 封鎖 | 使用者需求 |
| 免費或低成本 | 使用者需求 |
| 時程約 4 週:M1–M5 必交,M6 為加分題 | 使用者決定,2026-11-11 |
| 來源只保留 30 天:2026-10-14 12 時的資料查得到,2026-10-12 12 時已回空 | 實測,2026-11-11 |
| 來源會限速:每 2 秒一次請求,79 次中有 6 次回 429,`Retry-After` 約 26–32 秒。當時的 User-Agent 沒有聯絡方式 | 實測,2026-11-11 |
| Wikimedia 分級限速(每分鐘請求數,Action API 也適用):無識別資訊 10;合規 User-Agent、未登入 200;登入的新帳號 200;登入的資深編輯 2,000。合規 User-Agent 格式為 `<client>/<version> (<聯絡方式>)`,聯絡方式為網址或 email。建議同時請求不超過 3 個、遇 429 遵守 `Retry-After`,沒有該標頭時至少等 5 秒或指數退避。本專案未登入、一次一個請求,適用 200 次/分。該頁註明規則「2026 年新訂,可能調整」 | [Rate limits 頁](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits)(2026-11-08 版)與 [User-Agent 政策](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy)(2026-03-27 版),由 subagent 讀取原文後摘要,2026-11-12 |
| 雲端儲存:Neon Free 1 GB/專案,閒置 5 分鐘 suspend、連線時自動喚醒 | 官方方案頁,查證於 2026-11-07;部署前再確認 |
| 環境:Windows 10;Docker 29.7.2、Docker Compose v5.5.0 | 本機 `docker --version` 實測,2026-11-11 |

---

## 6. 資料來源

### 6.1 MediaWiki Action API 的 recentchanges

- 端點:`https://zh.wikipedia.org/w/api.php?action=query&list=recentchanges`,以 `rcstart`、`rcend` 指定時間窗,`rclimit=500` 分頁,以回應中的 `continue` 續抓。
- 不需註冊或金鑰。User-Agent 帶專案 repo 網址作為聯絡方式,不放個人 email。
- 每筆紀錄有流水號 `rcid`(每個維基各自編號)、`type`(`edit`、`new`、`log`、`categorize`)、`pageid`、`title`、`ns`、`user`、`userid`、`timestamp`、`oldlen`、`newlen`,以及逐筆的 `bot`、`minor` 旗標。
- `log` 類紀錄另有 `logtype`、`logaction`、`logparams`;`logparams` 的欄位隨日誌類型而不同,這是 raw 層用 JSONB 的理由。

實測的改名紀錄(2026-11-10,zhwiki):

```json
{"type": "log", "logtype": "move", "logaction": "move",
 "ns": 0, "title": "蘇柏傑", "pageid": 9656898, "rcid": 205403121,
 "timestamp": "2026-11-10T00:01:21Z",
 "logparams": {"target_ns": 118, "target_title": "Draft:蘇柏傑", "suppressredirect": ""}}
```

### 6.2 實測資料量(2026-11-10 UTC,實測於 2026-11-11)

| | zhwiki | enwiki |
|---|---|---|
| 12 時精確筆數 | 2,802(`rcid` 無重複;`bot` 839 筆) | 7,685(`bot` 859 筆) |
| 12 時的組成 | edit 2,069、categorize 678、new 28、log 27(其中 move 5) | edit 4,421、categorize 2,597、new 223、log 444(其中 move 30) |
| 全日(估計) | 約 4.1 萬列 | 約 35.4 萬列 |
| 30 天(估計) | 約 124 萬列 | 約 1,060 萬列 |
| 單小時最少 / 最多(`rcid` 跨距) | 1,086 / 2,854 | 6,192 / 40,122 |

量法:12 時為逐頁抓完的精確計數;其餘小時以 `rcid` 跨距推算,再以 12 時的比例校正(zhwiki 0.99、enwiki 0.95)。全日與 30 天為估計值,且只量了一天。

### 6.3 收錄範圍

- M1–M4 只收 zhwiki。所有表帶 `wiki` 欄位或鍵,加入其他語言版本不需改表結構。
- 回補 30 天,之後每小時增量。回補起點受來源的 30 天保留期限制:愈晚開始,能回補的最早日期愈晚。
- 進事實表的只有 `edit` 與 `new`。樣本小時中兩者共 2,097 筆,占 75%;依此比例,`fact_edit` 30 天約 93 萬列(估計)。

---

## 7. 架構與資料模型

架構圖:[`svg/arch.svg`](svg/arch.svg);星狀模型圖:[`svg/star.svg`](svg/star.svg);SCD2 範例:[`svg/scd2.svg`](svg/scd2.svg)。

M1–M4 所有層都在同一個本機 Postgres,以 schema 區分;M5 把 warehouse 層發布一份到 Neon。雲端那份是發布副本,不是管線直接寫入的目標。

| 層(schema) | 內容 |
|---|---|
| 落地檔(不在資料庫) | `data/landing/<wiki>/<小時>.jsonl.gz`:API 回應原樣存檔,一個小時一個檔。永不刪除,不進版控([ADR 0002](adr/0002-landing-files-before-raw.md)) |
| `raw` | `raw_recentchange`:原始 JSON(JSONB),唯一鍵 `(wiki, rcid)`;由落地檔載入。永不刪除 |
| `staging` | 型別化後的紀錄;分出「編輯與新建」「改名日誌」兩類供下游使用;小時級 DQ 在此把關 |
| `warehouse` | 事實表、維度表、`dq_results` |

### 7.1 事實表

| 表 | 粒度 | 主要欄位 | 備註 |
|---|---|---|---|
| `fact_edit` | 一次編輯或一次新建頁面 | `wiki_key`、`rcid`、`rev_id`、`page_sk`、`user_sk`、`date_key`、`event_ts`、`change_type`、`is_bot`、`is_minor`、`bytes_before`、`bytes_after`、`bytes_delta` | `bytes_delta` 可加總;以日(UTC)為分區載入 |
| `fact_page_daily` | 一個頁面 × 一天,只含當天至少有一次編輯的頁面 | `wiki_key`、`page_sk`、`date_key`、`edit_count`、`bytes_delta`、`bytes_end_of_day` | `bytes_end_of_day` 半可加:可跨頁面加總,不可跨日加總。不是每個頁面每天都有列;某天沒有列時,要取最近一次有紀錄的值 |

`is_bot` 放在事實表:來源的 `bot` 旗標是逐筆給的,同一帳號不一定每筆都標。

### 7.2 維度表

| 表 | 類型 | 主要欄位 |
|---|---|---|
| `dim_page` | SCD2 | `page_sk`、`wiki_key`、`page_id`、`title`、`namespace_id`、`valid_from`、`valid_to`、`is_current` |
| `dim_user` | SCD1 | `user_sk`、`wiki_key`、`user_id`、`user_name`、`is_anon` |
| `dim_date` | 靜態 | `date_key`、日期、週幾、週次、月份 |
| `dim_wiki` | 靜態 | `wiki_key`、代碼(`zhwiki`)、語言、網域 |

- 所有未登入的編輯對應到 `dim_user` 的同一列「匿名」,不儲存 IP 位址。來源以臨時帳號表示未登入編輯:`user` 形如 `~2026-59699-03`、`userid` 非 0、另帶 `temp: true`;2026-11-12 12 時的 1,709 筆中有 28 筆 `temp`,沒有任何一筆 `userid = 0` 或帶 `anon` 旗標(實測,2026-11-12,只量一個小時)。來源本身就不給 IP;`is_anon` 以 `temp` 旗標判定。臨時帳號要不要改成各自一列,M2 建 `dim_user` 時決定(第 14 節)。
- 日期一律以 UTC 計。

### 7.3 `dim_page` 的 SCD2 規則

- 追蹤屬性:`title`、`namespace_id`。兩者只會因 `move` 日誌而改變,而每次改變都有一筆帶時間的事件。
- 新版本的 `valid_from` = 改名事件的 `timestamp`;舊版本的 `valid_to` 填同一個時間,`is_current = false`。
- 頁面第一次出現時建立第一版,`valid_from` 設為開放起點(Postgres `-infinity`),屬性取自最早見到的那筆紀錄。回補區間之前的事件不會載入,所以不會有事實連到錯誤的版本;v0.1 的 `is_backdated` 欄位取消。
- 事實連結:`fact_edit` 的每一列連到 `event_ts` 落在 `[valid_from, valid_to)` 的那一版。
- 不追蹤保護狀態的理由:保護到期時自動失效,來源不產生事件;初始狀態也無法從事件流得知。

---

## 8. ETL 規則

| 主題 | 規則 |
|---|---|
| 擷取 | 每個小時窗 `[H, H+1)` 逐頁抓完;遇 429 依 `Retry-After` 等待後重試;API 呼叫限制為一次一個 |
| 冪等(raw) | `(wiki, rcid)` 衝突即略過(`ON CONFLICT DO NOTHING`) |
| 冪等(staging) | 以小時為單位,在單一交易內 delete 該小時後 insert |
| 冪等(fact) | 以日為單位,在單一交易內 delete 該日後 insert;失敗整段 rollback |
| 處理順序 | 維度先於事實:每日先更新 `dim_page`、`dim_user`,再載入事實表。日與日之間依序執行,一次只跑一日 |
| SCD2 | 當日的 `move` 事件依 `timestamp` 順序套用;同一事件重複套用不產生新版本 |
| SCD1 | 使用者名稱變更直接覆寫 |
| 重建 | 不支援對較早的日子做亂序重跑。需要時清空 warehouse 層,從 raw 依日序重播;這是 raw 永不刪除的理由之一 |
| 回補 | 每小時 DAG 以 Airflow catchup 補 30 天;每日 DAG 從回補區間的第一天起依序執行 |
| 保留 | raw 永不刪除;每週以 `pg_dump` 備份到本機另一個資料夾。來源只留 30 天,落地檔與 raw 是僅有的兩份副本,都在同一台筆電 |
| 轉換層 | 純 SQL(由 Airflow 呼叫);M6 用 dbt snapshot 重做 `dim_page` 對照 |

## 9. 資料品質與治理

| 規則類型 | 範例 | 執行時機 |
|---|---|---|
| 非空 | `rcid`、`pageid`、`timestamp` 不可為空 | 每小時 |
| 唯一 | staging 的 `(wiki, rcid)` 唯一;`dim_page` 每個 `(wiki, page_id)` 恰一列 `is_current = true` | 每小時 / 每日 |
| SCD2 區間 | 同一頁面的版本區間不重疊、不留空隙 | 每日 |
| 參照完整性 | `fact_edit.page_sk`、`user_sk` 都能在維度表找到 | 每日 |
| 新鮮度 | 最新一筆紀錄距今不超過 3 小時 | 每小時 |
| 量異常 | 單一小時筆數不低於 300 | 每小時 |
| 筆數對帳 | raw 該小時筆數 = staging 筆數 + 被剔除筆數;`fact_edit` 該日筆數 = staging 該日 `edit` 與 `new` 的筆數 | 每小時 / 每日 |

- 「3 小時」與「300 筆」是設計者給的起始值,不是量測出來的最佳值;M3 依實際資料調整。參考:實測單小時最少為 1,086 筆(第 6.2 節)。
- 量異常規則的由來:GH Archive 的量在一個月內三次斷崖(ADR 0001),來源變少時要第一時間知道。
- 結果寫入 `dq_results`(規則、分區、通過與否、實際值、執行時間);任一阻擋級規則失敗,下游任務不執行。另交付欄位血緣與資料字典文件。

## 10. 排程

| DAG | 頻率 | 步驟 | 執行限制 |
|---|---|---|---|
| `ingest_hourly` | 每小時 | 呼叫 API 抓該小時 → raw → staging → 小時級 DQ | catchup 開啟;各小時可亂序;API 呼叫共用一個 slot |
| `warehouse_daily` | 每日 | 等當日 24 個小時都完成 → `dim_page`(SCD2)→ `dim_user` → `fact_edit` → `fact_page_daily` → 每日 DQ →(M5 起)發布到 Neon | 依日序、一次一日 |

筆電關機期間的缺口由 catchup 補上,前提是缺口仍在來源的 30 天保留期內。

---

## 11. 分工(手寫清單)

| 由使用者手寫 | 由 AI 實作 |
|---|---|
| SCD2 merge SQL | Docker Compose、環境設定 |
| 冪等載入(raw 略過、staging 與 fact 分區覆寫) | Airflow DAG 骨架 |
| 資料品質檢查 | API 擷取(分頁、限速重試)、JSON 解析 |
| | 測試資料、CI、文件草稿 |

手寫項目的流程:AI 先給介面與會失敗的測試,使用者實作,AI 審查並挑戰。

## 12. 里程碑與驗收

| 里程碑 | 內容 | 驗收條件 |
|---|---|---|
| M1 | Compose + API 擷取 + raw 冪等載入;啟動 30 天回補 | 同一小時載入兩次,`raw_recentchange` 筆數不變;連續回補至少 3 天且所有 429 都重試成功;確認限速規則與未登入編輯的表示方式 |
| M2 | 星狀模型 + SCD2 | 合成變更資料(標示 synthetic)通過 SCD2 測試;真實 `move` 事件產生的版本數與 raw 的 `move` 筆數對得上;確認 `move` 之後舊紀錄的 `title` 是否會被來源改寫 |
| M3 | DQ | 每類規則各有一個注入壞資料的測試,皆被攔下並寫入 `dq_results` |
| M4 | Airflow | 兩個 DAG 跑完一段回補區間;任務失敗後重跑結果與一次跑完相同 |
| M5 | 雲端 + 文件 | warehouse 層發布至 Neon;業務問題 A、B、D 的 SQL 範例;README(英文)、ADR、資料字典、血緣、面試追問清單、K8s manifest、MLOps 設計文件;決定是否加入 enwiki |
| M6(加分題) | dbt 對照 | 以 dbt snapshot 重建 `dim_page`,與手寫版比較的結果寫成文件;時間不足則標示「未實作」 |

每個里程碑完成即 commit 到功能分支,並更新 `RESUME.md`。CI(GitHub Actions)在每次 push 跑 pytest。

---

## 13. 誠實揭露

| 限制 | 對外說法 |
|---|---|
| 題材與金融業無關 | 原選 GH Archive,設計階段實測發現來源退化後,以實測數字重新評估並改選(ADR 0001);選題看的是每小時增量、欄位不固定的 JSON、真的會變的維度 |
| 資料量小(30 天約百萬列) | 履歷寫實際筆數,不寫「大數據」;M5 評估加入 enwiki(約 10 倍)做索引前後對照 |
| 來源只保留 30 天 | 落地檔與 raw 層是僅有的兩份副本(同一台筆電),永不刪除;raw 每週備份 |
| SCD2 只追標題與命名空間 | 保護狀態到期時沒有事件,列為範圍外並寫明原因 |
| `fact_page_daily` 不是每日都有列 | 文件寫明只記有編輯的頁面,並示範如何取最近一次的值 |
| DQ 門檻是起始值 | 文件標示非量測最佳值,M3 調整 |
| 資料量為估計 | 只量了 2026-11-10 一天,數字附量法與日期 |
| K8s、MLOps 僅設計 | 履歷與 README 標示「設計、未實作」 |
| 免費額度與限速規則可能變動 | 數字附查證日期,部署前再確認 |

## 14. 未決問題

| 問題 | 何時決定 |
|---|---|
| ~~Wikimedia 各級限速的確切數字;是否需要登入帳號~~ 已確認(第 5 節):不需登入,合規 User-Agent 即 200 次/分 | 2026-11-12 |
| ~~未登入編輯在來源中的表示方式~~ 已確認(第 7.2 節):臨時帳號,帶 `temp: true` | 2026-11-12 |
| 臨時帳號在 `dim_user` 共用一列「匿名」,或各自一列(來源不給 IP,各自一列不涉及 IP) | M2 |
| 部分紀錄帶 `actionhidden`、`suppressed` 旗標(被隱藏的日誌),可能缺 `title` 或 `user`;staging 的非空規則要怎麼處理 | M2–M3 |
| ~~回補的落地檔是否列為正式的一層~~ 已決定保留(ADR 0002) | 2026-11-12 |
| `ingest_hourly` DAG 是否切成「落地」「載入」兩個任務 | M4 |
| `move` 之後,來源是否改寫舊紀錄的 `title`(影響能否加一條「事實的標題與維度版本一致」的對帳規則) | M2 |
| 新鮮度與量異常門檻的調整 | M3 |
| 是否加入 enwiki | M5 前 |
