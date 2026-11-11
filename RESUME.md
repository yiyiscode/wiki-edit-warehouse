# RESUME

更新:2026-11-11

## 目前進度
- spec 重審(grill)進行中。**`docs/SPEC.md`、`docs/overview.html`、`docs/svg/` 尚未更新,內容仍是舊的 GH Archive 版本,與下列決策衝突時以本檔為準。**
- 已 commit 到 `feat/spec` 分支。

## 2026-11-11 已定案的決策
1. **資料集改為維基百科 recentchanges API**,放棄 GH Archive + GitHub API。
   - 實測(2026-11-11):GH Archive 每小時 58,084 筆(2026-10-20 12 時)→ 2,958 筆(2026-11-09 12 時,PushEvent 為 0);收集器 repo 最後 push 為 2025-05-25。
   - 實測(2026-11-10 UTC 全日,估計值):zhwiki 約 4.1 萬列/日、30 天約 124 萬列;enwiki 約 35.4 萬列/日、30 天約 1,060 萬列。
   - recentchanges 只保留 30 天;間隔 2 秒請求仍偶發 429(Retry-After 約 30 秒)。
2. 收錄範圍:M1–M4 只收 zhwiki,表結構帶 `wiki` 欄位;M5 前再評估加 enwiki。
3. 資料庫:M1–M4 全在單一本機 Postgres(以 schema 分 raw/staging/warehouse);M5 才把 warehouse 層發布到雲端。
4. `dim_page` 的 SCD2 只追標題與命名空間(來自 `move` 事件);保護狀態為範圍外(到期時無事件)。
5. 更新順序:每小時 DAG 做 下載 → raw → staging → DQ;每日 DAG 先更新維度、再載事實表,天與天之間依序執行。
6. 先定 3–5 題業務問題寫進 SPEC 當驗收;M5 用 SQL 範例展示,不做儀表板。
7. 時程約 4 週:M1–M5 必交,M6(dbt 對照)為加分題。

## 下一步
1. 繼續 grill 尚未問的題目:
   - 業務問題選題(候選:各命名空間每日編輯量、改名前後活躍度、bot/人類/匿名占比、頁面大小成長)
   - 快照型事實表怎麼做(頁面每日位元組大小;只記有活動的頁面或全部)
   - 使用者維度欄位(SCD1;bot 旗標在事件上還是維度上)
   - 回補期間第一次見到的頁面,初始版本怎麼定
   - raw 層保留政策(來源只留 30 天,raw 是唯一副本)
   - 原 SPEC §14 未決項:雲端選 Neon 或 Supabase、新鮮度門檻
2. grill 結束後一次更新:`docs/SPEC.md`、`docs/overview.html`、`docs/svg/`(含 PNG)、memory;新增 ADR「為什麼放棄 GH Archive」。
3. M1 開工前補查:Wikimedia API 的官方限速規則。
4. M1:Docker Compose + raw 冪等載入(冪等載入由使用者手寫)。

## 關鍵決策
完整理由與替代方案見 memory `project-de-warehouse-decisions`;舊版決策見 `docs/SPEC.md`(待改寫)。
