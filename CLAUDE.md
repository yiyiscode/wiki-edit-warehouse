# CLAUDE.md

求職作品集專案:維基百科 recentchanges API → PostgreSQL 星狀資料倉儲。目標、範圍、驗收條件以 [`docs/SPEC.md`](docs/SPEC.md) 為準;動手前先讀它和 [`RESUME.md`](RESUME.md)。

## 分工

- **使用者手寫**:SCD2 merge SQL、冪等載入、資料品質檢查(SPEC §11)。輪到這些時,你先給介面(函式簽名、表結構)與會失敗的測試,讓使用者實作,再審查並挑戰。使用者明確說「你寫」才代寫。
- **你負責**:Docker、Airflow DAG 骨架、下載與解析、測試資料、CI、文件草稿等樣板。
- **架構決策屬於使用者**:給推薦、1–2 個替代方案與取捨,用 AskUserQuestion 交給使用者選;定案寫成 `docs/adr/` 的 ADR(中文)。發現使用者設計有盲點時直接指出。

## 誠實標示

這個專案要撐得住面試追問,所以:

- 合成資料一律標 `synthetic`(檔名、欄位或註解)。
- 只有設計沒有實作的內容,標「設計、未實作」。
- 外部數字(免費額度、API 限制、資料量)附查證日期。

## 工作流程

- 里程碑(SPEC §12)的驗收條件跑通才算完成;完成即 commit 到功能分支並更新 `RESUME.md`。
- 每張 SVG 用 `python scripts/svg2png.py <file.svg>` 同時匯出 PNG。
- README 用英文;SPEC、ADR、設計文件用中文。
