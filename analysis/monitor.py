"""
即時監測 algae_monitor_data.csv,偵測異常並發出警告。

用法:
    python monitor.py             # 持續執行(預設每 60 秒查一次)
    python monitor.py --once      # 只跑一次,適合手動測試
    python monitor.py --tail 5    # 只看最後 5 筆資料

警告管道(目前只記 console + log 檔):
    要加 email / Discord / LINE,改 send_alert() 函式即可
    log 檔在 ~/Desktop/alerts.log

異常判定:
    1. 硬閾值超出(立即警告,severity=high)
    2. 滑動 Z-score > 3σ(統計異常,severity=medium)
    3. 過去 30 分鐘該欄全是 -1(感測器斷線,severity=high)
"""
import sys
import time
import os
import pandas as pd
from datetime import datetime, timedelta

from config import (
    CSV_FILE, ALERT_LOG, SENSOR_COLS, HARD_LIMITS,
    CHECK_INTERVAL_SEC, ZSCORE_WINDOW_HOURS, ZSCORE_THRESHOLD,
    DISCONNECT_WINDOW_MIN,
    EMAIL_ENABLED, EMAIL_SENDER, EMAIL_APP_PASSWORD,
    EMAIL_RECEIVER, EMAIL_SUBJECT_PREFIX,
)
import smtplib
from email.mime.text import MIMEText


def load_data():
    """讀 CSV → DataFrame。空檔案或讀取失敗回空 DF"""
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    try:
        df = pd.read_csv(CSV_FILE, encoding='utf-8-sig')
    except Exception as e:
        print(f"讀 CSV 失敗: {e}")
        return pd.DataFrame()
    if '時間' not in df.columns:
        return pd.DataFrame()
    df['時間'] = pd.to_datetime(df['時間'], errors='coerce')
    df = df.dropna(subset=['時間']).set_index('時間').sort_index()
    return df


def check_hard_limits(df):
    """硬閾值:最新一筆超出範圍 → 警告"""
    if df.empty:
        return []
    latest = df.iloc[-1]
    alerts = []
    for col, (lo, hi) in HARD_LIMITS.items():
        if col not in df.columns:
            continue
        val = latest[col]
        if pd.isna(val) or val == -1:
            continue  # 斷線值不在這裡判定
        if val < lo or val > hi:
            alerts.append({
                'type': 'hard_limit',
                'sensor': col,
                'value': float(val),
                'limit': (lo, hi),
                'severity': 'high',
                'time': latest.name,
            })
    return alerts


def check_zscore(df):
    """滑動視窗 Z-score:當前值偏離過去 24 小時均值 > 3σ"""
    if len(df) < 30:
        return []
    cutoff = df.index[-1] - timedelta(hours=ZSCORE_WINDOW_HOURS)
    window = df[df.index >= cutoff]
    latest = df.iloc[-1]
    alerts = []
    for col in HARD_LIMITS.keys():
        if col not in df.columns:
            continue
        # 把 -1 過濾掉再算統計
        series = window[col].replace(-1, pd.NA).dropna().astype(float)
        if len(series) < 10:
            continue
        mean = series.mean()
        std = series.std()
        if std < 1e-6:
            continue  # 變異太小,跳過
        val = latest[col]
        if pd.isna(val) or val == -1:
            continue
        z = (val - mean) / std
        if abs(z) > ZSCORE_THRESHOLD:
            alerts.append({
                'type': 'zscore',
                'sensor': col,
                'value': float(val),
                'mean': float(mean),
                'z': float(z),
                'severity': 'medium',
                'time': latest.name,
            })
    return alerts


def check_disconnect(df):
    """過去 N 分鐘某欄全是 -1 → 感測器疑似斷線"""
    if df.empty:
        return []
    cutoff = df.index[-1] - timedelta(minutes=DISCONNECT_WINDOW_MIN)
    window = df[df.index >= cutoff]
    if len(window) == 0:
        return []
    alerts = []
    for col in HARD_LIMITS.keys():
        if col not in df.columns:
            continue
        if (window[col] == -1).all():
            alerts.append({
                'type': 'disconnect',
                'sensor': col,
                'severity': 'high',
                'time': window.index[-1],
            })
    return alerts


def format_alert(alert):
    """把 alert dict 轉成可讀字串"""
    sensor = alert['sensor']
    if alert['type'] == 'hard_limit':
        lo, hi = alert['limit']
        return (f"⚠️ [硬限警告] {sensor} = {alert['value']:.2f}, "
                f"超出正常範圍 [{lo}, {hi}]")
    elif alert['type'] == 'zscore':
        return (f"⚠️ [統計異常] {sensor} = {alert['value']:.2f}, "
                f"24h 均值 {alert['mean']:.2f}, Z = {alert['z']:+.2f}")
    elif alert['type'] == 'disconnect':
        return f"❌ [斷線] {sensor} 過去 {DISCONNECT_WINDOW_MIN} 分鐘讀值都是 -1,可能脫線"
    return str(alert)


def send_email(subject, body):
    """寄 email(Gmail SMTP)。設定不全則跳過。"""
    if not EMAIL_ENABLED:
        return
    if (not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECEIVER
            or "your_account" in EMAIL_SENDER or "xxxx" in EMAIL_APP_PASSWORD):
        print("⚠ Email 設定未完成,跳過寄信")
        return
    try:
        msg = MIMEText(body, _charset='utf-8')
        msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} {subject}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD.replace(" ", ""))
            server.send_message(msg)
    except Exception as e:
        print(f"⚠ Email 寄送失敗: {e}")


def send_alert(message):
    """發送警告:console + log 檔 + (若啟用)email"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {message}"
    print(full_msg)
    try:
        with open(ALERT_LOG, 'a', encoding='utf-8') as f:
            f.write(full_msg + "\n")
    except Exception as e:
        print(f"寫 log 失敗: {e}")
    # 從 message 抓警告類型作主旨
    if "硬限" in message:
        subject = "🔴 硬限警告"
    elif "斷線" in message:
        subject = "❌ 感測器斷線"
    elif "統計" in message:
        subject = "🟡 統計異常"
    else:
        subject = "通知"
    send_email(subject, full_msg)


def run_check_once(seen_alerts):
    """跑一輪檢查;回傳更新後的 seen_alerts(去重用)"""
    df = load_data()
    if df.empty:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 沒有資料")
        return seen_alerts

    all_alerts = (check_hard_limits(df) +
                  check_zscore(df) +
                  check_disconnect(df))

    fresh = []
    for a in all_alerts:
        key = (a['sensor'], a['type'])
        if key not in seen_alerts:
            fresh.append(a)
            seen_alerts.add(key)

    for a in fresh:
        send_alert(format_alert(a))

    # 沒有任何警告 → 清空已通知名單,下次有新狀況才會再發
    if not all_alerts and seen_alerts:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 所有狀況解除")
        seen_alerts = set()
    elif not fresh and not all_alerts:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 一切正常 ({len(df)} 筆資料)")

    return seen_alerts


def main():
    args = sys.argv[1:]
    once = '--once' in args

    print(f"=== 藻類監測警告系統啟動 ===")
    print(f"資料來源: {CSV_FILE}")
    print(f"警告 log: {ALERT_LOG}")
    print(f"檢查週期: {CHECK_INTERVAL_SEC} 秒")
    print()

    seen_alerts = set()
    while True:
        try:
            seen_alerts = run_check_once(seen_alerts)
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 監控錯誤: {e}")

        if once:
            break
        time.sleep(CHECK_INTERVAL_SEC)


if __name__ == "__main__":
    main()
