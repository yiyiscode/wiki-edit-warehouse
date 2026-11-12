# RESUME

更新:2026-11-12

## 目前進度
- spec 重審(grill)完成。`docs/SPEC.md` 已改寫為 v0.2:資料集由 GH Archive 改為維基百科 zhwiki 的 recentchanges API。
- 同步更新:`docs/overview.html`、`docs/svg/`(arch、star、scd2 及 PNG)、`CLAUDE.md` 的專案描述;新增 `docs/adr/0001-dataset-wikipedia-recentchanges.md`。
- 尚未開始寫程式。已 commit 到 `feat/spec` 分支。

## 下一步
- **M1:Docker Compose + API 擷取 + raw 冪等載入,並啟動 30 天回補。**
  - 來源只保留 30 天,愈晚開始能回補的最早日期愈晚,這一步有時間壓力。
  - AI 提供擷取程式(分頁、429 重試、含 repo 網址的 User-Agent)、介面與會失敗的測試;raw 冪等載入由使用者手寫。
  - M1 要順便確認的事(SPEC 第 14 節):Wikimedia 各級限速的確切數字、未登入編輯在來源中的表示方式。

## 關鍵決策
- 現行規格:`docs/SPEC.md` v0.2。
- 為什麼換資料集、實測數字、替代方案:`docs/adr/0001-dataset-wikipedia-recentchanges.md`。
- 白話版與選擇題:`docs/overview.html`。

## 設計者自行補上、使用者未逐項表態的細節
grill 時沒有單獨問,寫進 SPEC 前由設計者依已定案的決策推出;不同意請直接改 SPEC:
- 第四張維度表由「事件種類」改為 `dim_wiki`;編輯種類(`edit`/`new`)改成 `fact_edit` 上的欄位。
- 所有未登入編輯共用 `dim_user` 的一列「匿名」,不儲存 IP。
- 不支援對較早的日子亂序重跑;需要時清空 warehouse 層,從 raw 依日序重播。
- User-Agent 的聯絡方式用 repo 網址,不放個人 email。
- 專案代號暫定 `wiki-edit-warehouse`。
