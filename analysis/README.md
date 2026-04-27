# 分析模組

接收 `algae_monitor_data.csv`,提供:**即時警告 → 每日報告 → AI 分析**。

## 檔案總覽

| 檔案 | 用途 |
|---|---|
| `monitor.py` | 即時監測,異常時印 console、寫 log、寄 email |
| `daily_report.py` | 產生每日 HTML + 圖表報告 |
| `ai_report.py` | Claude API 寫日報(中文文字分析) |
| `config.py` | 共用設定(路徑、閾值、email 帳密) |
| `AI_REPORT_預估與樣本.md` | API 成本與輸出樣本 |
| `公開資料集調查.md` | 找過了,海水小球藻沒能直接用的公開資料 |

## 一次安裝

```bash
pip install pandas matplotlib anthropic
sudo apt install fonts-noto-cjk    # 樹梅派中文字體
```

## 用法

```bash
# 1) 監測警告(持續執行)
python monitor.py
python monitor.py --once         # 只跑一次

# 2) 每日報告(一次性,輸出到 ~/Desktop/daily_reports/)
python daily_report.py            # 處理昨天
python daily_report.py 2026-04-28
python daily_report.py --today    # 處理今天到目前

# 3) AI 寫日報(需要 Claude API key)
python ai_report.py --preview     # 不花錢,只看 prompt
export ANTHROPIC_API_KEY="sk-ant-..."
python ai_report.py
```

## 設定(`config.py`)

- **CSV 路徑** 已預設樹梅派桌面位置
- **硬閾值** 已依海水小球藻常見範圍預設;特殊藻種改 `HARD_LIMITS`
- **Email** 預設關閉,要開:把 `EMAIL_ENABLED = True`,填好 Gmail 三個欄位
  - 取得 Gmail 應用程式密碼:Google 帳戶 → 安全性 → 兩步驟驗證 → 應用程式密碼

## 樹梅派排程

```bash
crontab -e
0 7 * * *  cd /home/pi/algae && python3 analysis/daily_report.py    # 每天 7:00 出昨天報告
5 7 * * *  cd /home/pi/algae && python3 analysis/ai_report.py       # 7:05 加 AI 分析
```

monitor.py 持續跑用 `nohup` 或 systemd:
```bash
nohup python3 monitor.py > monitor.out 2>&1 &
```

## 詳細

- AI 日報的成本與樣本 → [AI_REPORT_預估與樣本.md](AI_REPORT_預估與樣本.md)
- 公開資料集為什麼不能用 → [公開資料集調查.md](公開資料集調查.md)
