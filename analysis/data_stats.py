"""
分析主 CSV 的感測器資料統計,用於決定 HARD_LIMITS。

用法:
    cd ~/AquaMind/analysis
    python3 data_stats.py            # 看全部資料
    python3 data_stats.py --days 3   # 只看最近 3 天

每顆感測器會印:
    N        : 有效樣本數(扣掉 -1/-2/-3 三種無資料代碼)
    mean     : 平均
    median   : 中位數(對極端值不敏感,通常比 mean 更代表「典型值」)
    std      : 標準差(波動大小)
    range    : 觀察到的最小 ~ 最大
    P1/P99   : 1%~99% 分位數(蓋住 98% 資料,排除最極端 1%)
    P5/P95   : 5%~95% 分位數(蓋住 90% 資料,排除最極端 5%)

設 HARD_LIMITS 的建議:
    用 P1/P99(或更寬的 min/max ± 安全緩衝)當警告閾值,
    讓 1% 真的極端的讀值才報警,99% 正常讀值不會誤報。
"""
import sys
import pandas as pd

from config import CSV_FILE, SENSOR_COLS
from sensor_codes import NO_DATA_CODES


def main():
    args = sys.argv[1:]
    days = None
    if '--days' in args:
        idx = args.index('--days')
        try:
            days = int(args[idx + 1])
        except (IndexError, ValueError):
            print("⚠ --days 後面要接整數,例如 --days 3")
            return

    print(f"讀取: {CSV_FILE}")
    df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    df['時間'] = pd.to_datetime(df['時間'], errors='coerce')
    df = df.dropna(subset=['時間']).sort_values('時間').reset_index(drop=True)

    if days is not None:
        cutoff = df['時間'].max() - pd.Timedelta(days=days)
        df = df[df['時間'] >= cutoff]
        print(f"過濾近 {days} 天")

    if df.empty:
        print("❌ 沒有任何有效資料")
        return

    print(f"總筆數: {len(df)}")
    print(f"時間範圍: {df['時間'].min()} ~ {df['時間'].max()}")
    print()

    no_data_list = list(NO_DATA_CODES)
    for col in SENSOR_COLS:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors='coerce')
        s = s[~s.isin(no_data_list)].dropna()

        print(f"=== {col} ===")
        if len(s) == 0:
            print("  無有效資料(整段都是 -1/-2/-3,可能未實裝)")
            print()
            continue

        # 每一種「無資料代碼」各佔多少
        raw = pd.to_numeric(df[col], errors='coerce')
        n_disc = int((raw == -1).sum())
        n_off = int((raw == -2).sum())
        n_miss = int((raw == -3).sum())

        print(f"  N有效 = {len(s):>5}   斷線(-1)={n_disc}  關閉(-2)={n_off}  未送(-3)={n_miss}")
        print(f"  mean   = {s.mean():>10.2f}   median = {s.median():>10.2f}   std = {s.std():>8.2f}")
        print(f"  range  = {s.min():>10.2f} ~ {s.max():.2f}")
        print(f"  P1     = {s.quantile(0.01):>10.2f}   P99    = {s.quantile(0.99):.2f}    (98% 資料的範圍)")
        print(f"  P5     = {s.quantile(0.05):>10.2f}   P95    = {s.quantile(0.95):.2f}    (90% 資料的範圍)")
        print()


if __name__ == "__main__":
    main()
