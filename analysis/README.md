# 分析模組

接收 `algae_monitor_data.csv`,提供:**即時 email 警告 + 網頁儀表板 + AI 日報**。

## 檔案總覽

| 檔案 | 跑在哪 | 用途 |
|---|---|---|
| `monitor_email.py` ✉ | 🍓 樹梅派(常駐) | 即時監測,異常時 console + log + email |
| `ai_report_email.py` ✉ | 🍓 樹梅派(每日 cron) | Claude API 寫日報 + 自動寄 email |
| `dashboard.py` | ☁️ Streamlit Cloud / 本機 | 網頁儀表板,讀 Google Sheets |
| `daily_report.py` | 🍓 樹梅派(每日 cron,可選) | 本地 HTML + matplotlib 圖表 |
| `email_helper.py` | (函式庫) | 共用寄信函式,給 `*_email.py` import |
| `config.py` | 🍓 樹梅派 | 共用設定(路徑、閾值、email 帳密) |
| `requirements.txt` | ☁️ | streamlit deploy 用相依 |
| `.streamlit/secrets.toml.example` | ☁️ | 部署 secrets 範本 |
| `AI_REPORT_預估與樣本.md` | 文件 | API 成本與輸出樣本 |
| `公開資料集調查.md` | 文件 | 為什麼海水小球藻沒有公開資料能訓練 |

> **檔名後綴 `_email` ✉** = 此程式會發 email,在 `config.py` 啟用後生效。

## 推薦架構

```
🍓 樹梅派(輕量)          ☁️ Streamlit Cloud
─────────────────         ───────────────────
rpi_gui_monitor.py        dashboard.py
   ↓                         ↑
algae_monitor_data.csv       │ 讀 csv export
   ↓ 上雲                     │
Google Sheets ─────────────────┘
   ↓
monitor_email.py(讀本地 csv,有異常→寄 email)
```

## 一次安裝(樹梅派)

```bash
sudo apt install python3-pandas python3-matplotlib python3-pip fonts-noto-cjk
pip3 install anthropic    # Pi 端裝這個就夠了
```

> Pi 3B 用 apt 而不是 pip 裝 pandas/matplotlib,避免編譯卡半小時

## 樹梅派端用法

```bash
# email 警告(常駐)
python3 monitor_email.py
python3 monitor_email.py --once     # 只跑一次測試

# 本地 HTML 日報(可選,如果你不想用 dashboard.py 也能在 Pi 跑)
python3 daily_report.py             # 處理昨天
python3 daily_report.py 2026-04-28
python3 daily_report.py --today

# AI 日報 + 寄 email
export ANTHROPIC_API_KEY="sk-ant-..."
python3 ai_report_email.py             # 產生 + 寄信
python3 ai_report_email.py --no-email  # 只存本地不寄信
python3 ai_report_email.py --preview   # 不花錢,只看 prompt
```

### 排程(crontab)
```bash
crontab -e
# 早上 7:00 出昨天本地 HTML 日報
0 7 * * * cd /home/pi/analysis && python3 daily_report.py
# 7:10 跑 AI 分析,產生 + 寄到 email
10 7 * * * cd /home/pi/analysis && python3 ai_report_email.py
```

### 持續執行 monitor_email.py
```bash
nohup python3 monitor_email.py > monitor.out 2>&1 &
```

## 網頁儀表板用法

### 本機跑(開發測試)
```bash
pip install -r requirements.txt
streamlit run dashboard.py
```
瀏覽器會自動打開 `http://localhost:8501`。

### 線上部署到 Streamlit Cloud(免費)

1. **把 `analysis/` 推上 GitHub**
2. https://share.streamlit.io 用 GitHub 帳號登入
3. 「New app」→ 選你的 repo,主檔填 `analysis/dashboard.py`
4. 點「**Advanced settings → Secrets**」,貼以下內容:
   ```toml
   GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/XXX/export?format=csv"
   ANTHROPIC_API_KEY    = "sk-ant-XXX"
   ```
5. Deploy → 拿到永久網址,**手機 / 電腦 / 評審都能看**

### Google Sheet 必須公開

1. 開 Sheet → 右上「共用」
2. 一般存取權改成「**知道連結的人**」、權限「檢視者」
3. 取得 CSV URL:把分享網址的 `/edit?gid=0` 換成 `/export?format=csv`

## 設定(`config.py`)

- **CSV 路徑** 預設樹梅派桌面
- **硬閾值** 已依海水小球藻常見範圍預設
- **Email** 預設 `EMAIL_ENABLED = False`,啟用時:
  1. 取得 Gmail 應用程式密碼:Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼
  2. 填入 `EMAIL_SENDER` / `EMAIL_APP_PASSWORD` / `EMAIL_RECEIVER`
  3. 改為 `EMAIL_ENABLED = True`

## 其他

- AI 日報的成本與樣本 → [AI_REPORT_預估與樣本.md](AI_REPORT_預估與樣本.md)
- 為什麼公開資料集對小球藻沒幫助 → [公開資料集調查.md](公開資料集調查.md)
