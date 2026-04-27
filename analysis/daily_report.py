"""
產生每日報告:統計表 + 時序圖 + 生長趨勢 + 相關係數熱力圖 + HTML 整合。

用法:
    python daily_report.py                # 處理「昨天」的資料
    python daily_report.py 2026-04-28     # 處理指定日期
    python daily_report.py --today        # 處理「今天到目前」的資料

輸出:
    ~/Desktop/daily_reports/YYYY-MM-DD/
        ├── report.html       ← 整合報告(瀏覽器開啟)
        ├── timeseries.png
        ├── growth.png
        ├── correlation.png
        └── stats.csv

設定 cron(樹梅派每天早上 7:00 產生昨天的報告):
    crontab -e
    0 7 * * * cd /home/pi/algae && python3 analysis/daily_report.py
"""
import sys
import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from config import (
    CSV_FILE, REPORT_DIR, SENSOR_COLS, FONT_FAMILY,
)

# 中文字體設定
matplotlib.rcParams['font.sans-serif'] = FONT_FAMILY
matplotlib.rcParams['axes.unicode_minus'] = False


def load_day(target_date, today_so_far=False):
    """載入指定日期的資料"""
    if not os.path.exists(CSV_FILE):
        print(f"❌ 找不到 CSV: {CSV_FILE}")
        return pd.DataFrame()

    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    if '時間' not in df.columns:
        print(f"❌ CSV 缺少「時間」欄位")
        return pd.DataFrame()

    df['時間'] = pd.to_datetime(df['時間'], errors='coerce')
    df = df.dropna(subset=['時間'])

    start = pd.Timestamp(target_date)
    if today_so_far:
        end = pd.Timestamp(datetime.now())
    else:
        end = start + pd.Timedelta(days=1)

    day_df = df[(df['時間'] >= start) & (df['時間'] < end)]
    return day_df.set_index('時間').sort_index()


def replace_disconnect(df):
    """把 -1(斷線值)換成 NaN,免得拖累統計"""
    return df.replace(-1, pd.NA).infer_objects(copy=False)


def stats_table(df):
    """每個感測器的當日統計"""
    cols = [c for c in SENSOR_COLS if c in df.columns]
    clean = replace_disconnect(df[cols]).astype(float)
    stats = pd.DataFrame({
        '最小': clean.min(),
        '平均': clean.mean(),
        '最大': clean.max(),
        '標準差': clean.std(),
        '有效筆數': clean.count(),
        '斷線筆數': (df[cols] == -1).sum(),
    })
    return stats.round(2)


def plot_timeseries(df, output_path):
    """所有感測器的時序圖,垂直堆疊"""
    cols = [c for c in SENSOR_COLS if c in df.columns]
    clean = replace_disconnect(df[cols]).astype(float)
    fig, axes = plt.subplots(len(cols), 1, figsize=(14, 2 * len(cols)), sharex=True)
    if len(cols) == 1:
        axes = [axes]
    for ax, col in zip(axes, cols):
        ax.plot(clean.index, clean[col], linewidth=1)
        ax.set_ylabel(col, fontsize=10)
        ax.grid(True, alpha=0.3)
        # 標出 -1 斷線時段(顯示成紅色短橫條於底部)
        disc = df[df[col] == -1].index
        if len(disc) > 0:
            ax.scatter(disc, [ax.get_ylim()[0]] * len(disc),
                       color='red', s=4, marker='|', label='斷線')
    axes[-1].set_xlabel('時間')
    fig.suptitle("當日感測器時序", y=0.995, fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()


def plot_correlation(df, output_path):
    """變數相關係數熱力圖"""
    cols = [c for c in SENSOR_COLS if c in df.columns]
    clean = replace_disconnect(df[cols]).astype(float)
    # 過濾全空欄位
    cols = [c for c in cols if clean[c].notna().any()]
    clean = clean[cols]
    corr = clean.corr()

    fig, ax = plt.subplots(figsize=(11, 9))
    im = ax.imshow(corr, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    ax.set_xticks(range(len(cols)))
    ax.set_yticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha='right')
    ax.set_yticklabels(cols)

    for i in range(len(cols)):
        for j in range(len(cols)):
            v = corr.iloc[i, j]
            if pd.isna(v):
                txt = "N/A"
            else:
                txt = f"{v:.2f}"
            ax.text(j, i, txt, ha="center", va="center",
                    color="white" if abs(v) > 0.5 else "black", fontsize=9)

    plt.colorbar(im, ax=ax, label="相關係數")
    ax.set_title("感測器相關性(海水藻類監測)", fontweight='bold')
    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()


def plot_growth(df, output_path):
    """濁度當生長代理,看每小時生長率"""
    if "濁度(NTU)" not in df.columns:
        return False
    clean = replace_disconnect(df[["濁度(NTU)"]]).astype(float)
    if clean["濁度(NTU)"].notna().sum() < 5:
        return False

    hourly = clean.resample('1h').mean()
    growth = hourly.diff()

    fig, axes = plt.subplots(2, 1, figsize=(14, 7), sharex=True)
    axes[0].plot(hourly.index, hourly["濁度(NTU)"], 'g-', linewidth=2, marker='o')
    axes[0].set_ylabel('濁度 (NTU)', fontsize=11)
    axes[0].set_title("濁度趨勢(代理藻類密度)", fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3)

    colors = ['#2e7d32' if x > 0 else '#c62828'
              for x in growth["濁度(NTU)"].fillna(0)]
    axes[1].bar(growth.index, growth["濁度(NTU)"].values,
                width=0.035, color=colors)
    axes[1].axhline(0, color='black', linewidth=0.5)
    axes[1].set_ylabel('每小時變化量 (NTU/hr)', fontsize=11)
    axes[1].set_xlabel('時間', fontsize=11)
    axes[1].set_title("每小時生長率(綠 = 增加,紅 = 減少)", fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=100, bbox_inches='tight')
    plt.close()
    return True


def make_html(target_date, df, stats, has_growth, out_dir):
    """整合 HTML 報告"""
    title_date = target_date.strftime('%Y-%m-%d')
    gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    growth_section = (
        f'<h2>🌱 生長趨勢(濁度為代理)</h2><img src="growth.png" alt="生長趨勢">'
        if has_growth else
        '<h2>🌱 生長趨勢</h2><p>濁度資料不足,無法產生生長圖</p>'
    )

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <title>藻類監測日報 — {title_date}</title>
    <style>
        body {{
            font-family: 'Microsoft JhengHei', 'Noto Sans CJK TC', sans-serif;
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            background: #fafafa;
            color: #222;
        }}
        h1 {{ color: #2e7d32; border-bottom: 2px solid #2e7d32; padding-bottom: 8px; }}
        h2 {{ color: #555; margin-top: 32px; border-left: 4px solid #2e7d32; padding-left: 10px; }}
        .meta {{ color: #888; font-size: 14px; }}
        table {{
            border-collapse: collapse; width: 100%; margin: 10px 0;
            background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: right; }}
        th {{ background: #2e7d32; color: white; }}
        td:first-child, th:first-child {{ text-align: left; }}
        img {{
            width: 100%; max-width: 1100px; margin: 12px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
            background: white;
        }}
    </style>
</head>
<body>
    <h1>🌱 藻類監測日報 — {title_date}</h1>
    <p class="meta">產生時間:{gen_time}<br>
    有效資料筆數:{len(df)}</p>

    <h2>📊 當日統計</h2>
    {stats.to_html(border=0)}

    <h2>📈 全天時序</h2>
    <img src="timeseries.png" alt="時序圖">

    {growth_section}

    <h2>🔗 環境變數相關性</h2>
    <p>看哪些感測器讀值會「一起動」(正相關 = 紅,負相關 = 藍)</p>
    <img src="correlation.png" alt="相關係數">

    <hr style="margin-top:40px;">
    <p class="meta">本報告由 daily_report.py 自動產生</p>
</body>
</html>"""

    html_path = os.path.join(out_dir, 'report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return html_path


def make_report(target_date, today_so_far=False):
    df = load_day(target_date, today_so_far=today_so_far)
    if df.empty:
        print(f"❌ {target_date} 沒有有效資料")
        return None

    out_dir = os.path.join(REPORT_DIR, target_date.strftime('%Y-%m-%d'))
    os.makedirs(out_dir, exist_ok=True)

    print(f"產生報告:{target_date}({len(df)} 筆資料)")

    # 圖表
    plot_timeseries(df, os.path.join(out_dir, 'timeseries.png'))
    plot_correlation(df, os.path.join(out_dir, 'correlation.png'))
    has_growth = plot_growth(df, os.path.join(out_dir, 'growth.png'))

    # 統計
    stats = stats_table(df)
    stats.to_csv(os.path.join(out_dir, 'stats.csv'), encoding='utf-8-sig')

    # HTML
    html_path = make_html(target_date, df, stats, has_growth, out_dir)

    print(f"✓ 完成")
    print(f"  HTML: {html_path}")
    print(f"  Folder: {out_dir}")
    return html_path


def main():
    args = sys.argv[1:]
    today_so_far = '--today' in args

    if today_so_far:
        target = datetime.now().date()
    elif args and not args[0].startswith('--'):
        target = pd.Timestamp(args[0]).date()
    else:
        target = (datetime.now() - timedelta(days=1)).date()

    make_report(target, today_so_far=today_so_far)


if __name__ == "__main__":
    main()
