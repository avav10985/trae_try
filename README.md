# AquaMind 🌊

> 海水藻類培養的即時環境監測系統 — 從感測器到雲端儀表板與 AI 日報的完整方案。

針對**海水小球藻**等海洋微藻培養設計,以 Arduino + Raspberry Pi 採集 9 項水質參數,經 Google Sheets 上雲,提供網頁儀表板、即時 email 警告、與 Claude 自動撰寫的中文日報。

---

## 系統架構

整個系統分成 **3 個區段**,每段在不同地方運作、做不同的事:

### 🔬 感測端 — 「在水裡量」
**位置:** 養殖桶旁邊
**硬體:** Arduino UNO + 7 顆水質感測器
**做什麼:** 每 10 秒量一次水的溫度、pH、含鹽量、濁度、CO₂、光照……,然後把數據透過 USB 線傳給樹莓派
**主程式:** [`uno_sensor_serial.ino`](uno_sensor_serial/uno_sensor_serial.ino)(燒進 Arduino 一次,之後它自己跑)

### 🍓 本地端 — 「在家裡的小電腦處理」
**位置:** 家裡,接著 Arduino + 接著 Wi-Fi
**硬體:** Raspberry Pi(樹莓派,信用卡大小的電腦)
**做什麼:** 接收 Arduino 量到的數據,然後做兩件事:
  - **① 存一份在桌面**(本地備份,即使網路掛了也不會掉資料)
  - **② 把同一筆送上雲端**(讓你出門也能看)

**主程式:** [`rpi_gui_monitor.py`](rpi_gui_monitor.py)(Pi 開機就要跑)

**附加功能**(可選,也在 Pi 上跑):
| 程式 | 做什麼 |
|---|---|
| ✉ [`monitor_email.py`](analysis/monitor_email.py) | 數據異常 → 立刻寄 email 通知你 |
| 📊 [`daily_report.py`](analysis/daily_report.py) | 每天自動產生圖表 HTML 報告(本地檔) |
| 🤖 [`ai_report_email.py`](analysis/ai_report_email.py) | 每天請 Claude AI 寫一段文字日報並寄到信箱 |

### ☁ 線上端 — 「網路上看得到」
**位置:** Google 和 Streamlit 公司的伺服器(**不是**你的電腦)
**做什麼:** 把雲端那份資料變成漂亮的網頁,**任何人有網址都能看**(電腦、手機、平板都行)
**靠的是兩個免費服務串起來:**
  - **Google 試算表** — 像 Excel 但在雲端,Pi 把數據傳這裡;[`googlecsv.js`](googlecsv.js) 是接收程式
  - **Streamlit Cloud** — 把試算表變成有圖表、4 個分頁的網頁;[`dashboard.py`](analysis/dashboard.py) 是網頁本身

**目前網址:** `https://aquamind-algae.streamlit.app`

### 一張圖把三段串起來

```
🔬 感測端                    🍓 本地端                       ☁ 線上端
┌──────────┐ USB線  ┌────────────────────────┐  網路   ┌────────────────┐
│ Arduino   │ ───▶  │ 樹莓派 Raspberry Pi     │  ────▶ │ Google 試算表   │
│ + 7 感測器│        │ (24 小時開著)            │         └────┬───────────┘
└──────────┘       │                         │              │
養殖桶              │  存到桌面 CSV ◀──┐       │              ▼
                   │                  │       │         ┌─────────────┐
                   │  寄 email ──────┐ │       │         │ Streamlit   │
                   │                 │ │       │         │ 網頁儀表板   │
                   │  AI 日報 ───────┤ │       │         └─────┬───────┘
                   └─────────────────┘─┘       │               │
                          ↓                                    ▼
                       ✉ Gmail                          手機/電腦看網址
```

### 監測項目(7 顆感測器)

| 項目 | 感測器 | 海水建議範圍 |
|---|---|---|
| 溫度 | DS18B20 | 15–35 °C |
| 酸鹼 (pH) | SEN0169 | 6.5–9.5 |
| 溶解固體 (TDS) | SEN0244 | — |
| 導電度 (EC) | DFR0300 | 25–60 mS/cm |
| 濁度 | SEN0189 | 0–3000 NTU |
| 光照 | BH1750 | 0–50000 lx |
| CO₂ | MH-Z19C | 200–5000 ppm |

> **TDS(EC)** 是用 EC 公式算出來的衍生值(SEN0244 在海水會飽和,改用 EC 推算 TDS),不是獨立感測器。
> 程式預留**第 2 顆 CO₂ (MH-Z19B)** 位置,目前未實裝,讀值固定 -1;未來插上去不用改程式。

---

## 專案結構

```
AquaMind/
├── analysis/                         # ☁ 雲端 / Pi 端分析模組
│   ├── dashboard.py                    Streamlit 網頁儀表板(4 分頁)
│   ├── monitor_email.py        ✉      即時監測 + 異常 email 警告
│   ├── ai_report_email.py      ✉      Claude API 撰寫 AI 日報 + 寄信
│   ├── daily_report.py                每日本地 HTML 圖表
│   ├── email_helper.py                共用寄信函式庫
│   ├── config.py                      閾值 / 路徑 / Email 設定
│   └── README.md                      模組詳細說明
│
├── uno_sensor_serial/                # Arduino UNO 感測器主程式
├── esp32_sensor_serial.ino           # ESP32 序列傳輸版
├── esp32_sensor_mqtt.ino             # ESP32 MQTT 版
├── esp32_test_serial/                # ESP32 測試
├── uno_sensor_serial_with_temp_comp.ino  # 含溫度補償的舊版
├── uno_test_serial.ino               # Arduino 測試
│
├── rpi_gui_monitor.py                # 🍓 Pi 端主接收 GUI(Tkinter)
├── rpi_gui_monitor1.py               # GUI 變體
├── rpi_receiver.py                   # 純 console 接收器
├── rpi_multi_serial_receiver.py      # 多串口接收
├── rpi_data_slicer.py                # CSV 切片工具
├── googlecsv.js                      # Google Apps Script:CSV → Sheets
│
├── 校準程式/                          # 各感測器校準 sketch
│   ├── PH/  PH_TwoPoint/  PH_EEPROM_Reset/    # SEN0169 用 PH_TwoPoint 校準
│   ├── PH_SEN0161v2_DO_NOT_USE/                # ⚠ 公式對 SEN0169 是錯的,留作參考
│   ├── ECDRF0300/  TDS/  CO2_MHZ19/
│
├── 備用程式/                          # 已知可運作的穩定版本快照
└── 對話紀錄/                          # 開發過程的對話紀錄
```

> **檔名後綴 `_email`** ✉ = 此程式啟用後會發 email。

---

## 線上儀表板

部署於 Streamlit Cloud,4 個分頁:

| 分頁 | 功能 |
|---|---|
| 📊 即時數據 | 7 顆感測器最新讀值,異常自動標紅,24h 互動圖 |
| 📈 歷史趨勢 | 自選感測器 / 時段,plotly 互動圖含閾值線 + 統計表 |
| ⚠ 異常分析 | 時段內所有硬限超出事件清單,加斷線次數柱狀圖 |
| 🤖 AI 日報 | 選日期 → 點按鈕呼叫 Claude → 即時產生中文分析 + 下載 |

---

## 快速開始

### 1. 硬體端(Arduino + Raspberry Pi)

把 [`uno_sensor_serial/uno_sensor_serial.ino`](uno_sensor_serial/uno_sensor_serial.ino) 燒進 Arduino,Pi 端跑:

```bash
python3 rpi_gui_monitor.py        # 接收 + 寫入 CSV
```

### 2. 上傳到 Google Sheets

把 [`googlecsv.js`](googlecsv.js) 部署成 Google Apps Script Web App,Pi 透過 HTTP 上傳。

### 3. 雲端儀表板(Streamlit)

```bash
cd analysis
pip install -r requirements.txt
streamlit run dashboard.py
```

部署到 Streamlit Cloud 詳見 [`analysis/README.md`](analysis/README.md)。

### 4. Email 警告 / AI 日報(Pi 排程)

```bash
crontab -e
0 7 * * *  cd /home/pi/analysis && python3 daily_report.py
10 7 * * * cd /home/pi/analysis && python3 ai_report_email.py
```

詳細設定見 [`analysis/README.md`](analysis/README.md)。

---

## 相依

- **Arduino**: DallasTemperature, OneWire, BH1750, DFRobot_PH, MHZ19
- **Raspberry Pi**: `pyserial`, `pandas`, `matplotlib`, `requests`
- **雲端**: `streamlit`, `plotly`, `anthropic` — 見 [`analysis/requirements.txt`](analysis/requirements.txt)

---

## 文件

- [`analysis/README.md`](analysis/README.md) — 分析模組完整使用說明
- [`analysis/AI_REPORT_預估與樣本.md`](analysis/AI_REPORT_預估與樣本.md) — Claude API 成本與輸出樣本
- [`analysis/公開資料集調查.md`](analysis/公開資料集調查.md) — 為什麼海水小球藻沒有公開資料集可用

---

## 授權

僅限學術 / 競賽用途。
