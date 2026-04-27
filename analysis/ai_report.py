"""
AI 自動寫日報(Claude API)。

用法:
    # 設環境變數後執行
    export ANTHROPIC_API_KEY="sk-ant-..."
    python ai_report.py                # 處理昨天
    python ai_report.py 2026-04-28     # 處理指定日期

    # 沒設 API key 時,只會印 prompt 預覽不真正呼叫 API(免費)
    python ai_report.py --preview

模型:
    預設 claude-haiku-4-5(最便宜,日報夠用)
    要更高品質改 MODEL = "claude-sonnet-4-6"

成本(每天約 1 次):
    Haiku 4.5  ≈ $0.003 USD/天 ≈ $0.10/月
    Sonnet 4.6 ≈ $0.01  USD/天 ≈ $0.30/月
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta

from config import CSV_FILE, SENSOR_COLS, REPORT_DIR

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-haiku-4-5"
MAX_TOKENS = 600


def load_day(target_date):
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    if '時間' not in df.columns:
        return pd.DataFrame()
    df['時間'] = pd.to_datetime(df['時間'], errors='coerce')
    df = df.dropna(subset=['時間'])
    start = pd.Timestamp(target_date)
    end = start + pd.Timedelta(days=1)
    return df[(df['時間'] >= start) & (df['時間'] < end)].set_index('時間').sort_index()


def summarize(df):
    """把當日資料壓縮成精簡摘要文字"""
    cols = [c for c in SENSOR_COLS if c in df.columns]
    clean = df[cols].replace(-1, pd.NA).infer_objects(copy=False).astype(float)

    lines = []
    for col in cols:
        s = clean[col].dropna()
        if len(s) == 0:
            lines.append(f"- {col}: 全程斷線(無資料)")
            continue
        first, last = s.iloc[0], s.iloc[-1]
        delta = last - first
        lines.append(
            f"- {col}: 平均 {s.mean():.2f}, 範圍 {s.min():.2f}~{s.max():.2f}, "
            f"日內變化 {delta:+.2f}"
        )

    # 斷線統計
    disc_count = (df[cols] == -1).sum()
    disc_lines = [f"- {col}: {n} 筆" for col, n in disc_count.items() if n > 0]

    out = [
        f"資料筆數:{len(df)}",
        "",
        "各感測器當日統計:",
        *lines,
    ]
    if disc_lines:
        out += ["", "斷線時段(讀值=-1):", *disc_lines]
    return "\n".join(out)


def build_prompt(target_date, stats_text):
    return f"""你是水產養殖與藻類培養專家。以下是 {target_date} 一日的「海水小球藻」(marine Chlorella)監測數據摘要:

{stats_text}

請以繁體中文撰寫日報,包含:
1. **總體判斷**:藻類狀態(良好 / 普通 / 需警戒),一句話即可
2. **3 個重點觀察**:濁度趨勢、pH 變化、CO2 與光照協同等(挑最重要的)
3. **需警戒的異常**:若有
4. **明日操作建議**:光照、CO2 添加、換水、稀釋等具體動作

控制在 250 字以內,直接寫,不要客套也不要重複數據。"""


def call_claude(prompt):
    """呼叫 Claude API。沒裝 anthropic 或沒 API key → 回 None"""
    if not API_KEY:
        return None
    try:
        from anthropic import Anthropic
    except ImportError:
        print("⚠ 缺 anthropic 套件,執行: pip install anthropic")
        return None
    client = Anthropic(api_key=API_KEY)
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text, msg.usage
    except Exception as e:
        print(f"Claude API 錯誤: {e}")
        return None


def save_report(target_date, response_text):
    """把 AI 報告寫到當日 daily_report 資料夾"""
    out_dir = os.path.join(REPORT_DIR, target_date.strftime('%Y-%m-%d'))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'ai_report.md')
    header = f"# AI 日報 — {target_date.strftime('%Y-%m-%d')}\n"
    header += f"\n模型:`{MODEL}`  \n產生時間:{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(header + response_text)
    return out_path


def main():
    args = sys.argv[1:]
    preview = '--preview' in args

    # 取得目標日期
    date_args = [a for a in args if not a.startswith('--')]
    if date_args:
        target = pd.Timestamp(date_args[0]).date()
    else:
        target = (datetime.now() - timedelta(days=1)).date()

    df = load_day(target)
    if df.empty:
        print(f"❌ {target} 沒有資料")
        return

    stats_text = summarize(df)
    prompt = build_prompt(target.strftime('%Y-%m-%d'), stats_text)

    if preview or not API_KEY:
        print("=== Prompt 預覽(未呼叫 API)===\n")
        print(prompt)
        if not API_KEY:
            print("\n💡 設 ANTHROPIC_API_KEY 環境變數後即可實際產生 AI 日報")
        return

    print(f"呼叫 {MODEL} ...")
    result = call_claude(prompt)
    if result is None:
        return
    text, usage = result
    out_path = save_report(target, text)
    print(f"\n✓ 已寫入:{out_path}")
    print(f"\n--- AI 日報內容 ---\n{text}")
    print(f"\n--- Token 用量 ---")
    print(f"input:  {usage.input_tokens}")
    print(f"output: {usage.output_tokens}")


if __name__ == "__main__":
    main()
