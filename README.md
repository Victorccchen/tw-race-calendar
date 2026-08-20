# 島嶼賽事曆 — 後端

台灣戶外賽事與體驗活動的資料管線。每日抓取多來源、比對異動、訂版快照、重建靜態網站。

## 每日流程

```
refresh.py
  ├─ 1. 抓取六個來源            sources/*.py
  ├─ 2. 正規化 + 去重 + 過濾過期   lib/normalize.py
  ├─ 3. 連結存活檢查（前 90 筆）
  ├─ 4. 與昨日快照比對            lib/diff.py
  ├─ 5. 訂版：data/snapshots/YYYY-MM-DD.json（永久保留）
  ├─ 6. 異動清單：data/changes/YYYY-MM-DD.{md,json}
  └─ 7. 重建網站：site/index.html（樣板 + 資料）
```

**自動偵測、人工放行**：異動清單只產出報告，不會自動改動前台資料的判讀。
網站每天照常重建，但「這筆異動是否代表賽事真的改期」由人確認。

## 資料來源

| 模組 | 來源 | 性質 | 可靠度 |
|---|---|---|---|
| `biji.py` | 運動筆記 | HTML，欄位最全（含報名開窗） | 高 |
| `isports.py` | i運動資訊平台（教育部體育署） | 官方 REST，免 API key | 高 |
| `kktix.py` | KKTIX 組織 API | 官方 JSON（Spartan 等商業主辦） | 高 |
| `ctta.py` | 中華民國網球協會 9 個分類頁 | HTML | 中（日期需從標題／摘要解析） |
| `sunmoonlake.py` | 日月潭國家風景區管理處 | 靜態 HTML，穩定 | 高 |
| `indie.py` | 主辦方名冊（野托邦、X-Camp、Fun3sport ForceKids） | WordPress REST API + 人工驗證 | 高 |

### 主辦方優先原則

聚合平台（伊貝特、活動咖、EventGo）**只用來發現主辦方，不作為資料來源**。
找到主辦方後，一律回其官網取得賽期與報名連結——聚合站的資料常落後或不完整。

伊貝特（bao-ming.com）有人機驗證（CAPTCHA），不抓取，僅作為報名連結提供給使用者。

主辦方名冊在 `data/indie_operators.json`，每個主辦標記 `adapter`：

| adapter | 抓法 |
|---|---|
| `wp` | WordPress REST API（`/wp-json/wp/v2/posts`），依分類與關鍵字過濾公告 |
| `none` | 純人工維護（SPA 或社群頁，無法穩定解析） |

自動撈到的場次**一律先進待驗證佇列**，人工確認後寫進名冊並標上 `verified`，
才會出現在前台。這是「寧缺勿濫」的落實方式。

**為什麼不爬 Facebook**：Meta 已封鎖未登入訪客讀取粉專內容，官方 Graph API 讀取
Page Feed 需通過 App Review 的 `Page Public Content Access`，且版本汰換頻繁。
改採「跟著報名系統走」——賽事公告在 FB，但報名一定會落地到 KKTIX、伊貝特或官網。

**常態開課**：野托邦（MTB）依梯次滾動開班，非單一日期賽事，於 `curated.py`
以 `recurring` 標記，ICS 產生時輸出為週期性事件。

## 線上位址

| 用途 | 網址 |
|---|---|
| 賽事曆 | https://tw-race-calendar.vercel.app |
| 行事曆訂閱（全部） | https://tw-race-calendar.vercel.app/ics |
| 訂閱（篩選） | `/ics?sport=run,trail&city=臺中&kids=1&type=exp,camp` |

訂閱時 Apple 行事曆用 `webcal://`，Google 行事曆用 `https://`。
每筆賽事一則全天事件，另為有報名截止日者各產生一則「【報名截止】」提醒。
常態開課（野托邦等）以 RRULE 輸出為週期性事件。

Vercel 專案：`victorccchens-projects/tw-race-calendar`。
`scheduler/daily.sh` 偵測到 `web/.vercel` 存在時，會在每日刷新後自動部署。

## 指令

```bash
python3 refresh.py              # 完整跑一次（含連結檢查）
python3 refresh.py --no-links   # 跳過連結檢查，較快
python3 refresh.py --dry        # 只比對、印出清單，不寫入
```

## 排程

launchd 每日 07:10 執行 `scheduler/daily.sh`。

```bash
launchctl list | grep racecal                                   # 確認狀態
launchctl unload ~/Library/LaunchAgents/tw.racecal.daily.plist  # 停用
launchctl load   ~/Library/LaunchAgents/tw.racecal.daily.plist  # 啟用
```

日誌 `logs/YYYY-MM-DD.log`，保留 90 天；快照同樣保留 90 天；異動清單永久保留。

## 目錄

```
sources/     各來源抓取模組（互相獨立，單一來源失敗不影響其他）
lib/         normalize.py 分類正規化、diff.py 異動比對
data/
  events.json          目前有效資料（網站用）
  snapshots/           每日訂版快照
  changes/             每日異動清單 .md / .json
site/
  template.html        版型（含 __DATA__ 佔位符）
  index.html           產出的網站
scheduler/   daily.sh + launchd plist
```

## 已知限制

- 連結檢查每日只驗前 90 筆，避免對來源站造成負擔；`HTTP 403/405` 視為拒絕 HEAD 而非失效。
- 卡片照片為 AI 生成的運動情境示意圖，依運動類型共用，非各賽事實際照片。
- CTTA 日期解析依賴標題的 `[MMDD-MMDD]` 前綴或摘要中的民國年，格式異常時該筆會被略過。
