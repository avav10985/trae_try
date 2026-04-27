import os
import time
import csv
from datetime import datetime

# --- 設定 ---
# 這裡會自動指向樹莓派桌面
DESKTOP_PATH = os.path.expanduser("~/Desktop")
# 監控的主檔案名稱（需與 GUI 程式設定的一致）
MAIN_CSV = os.path.join(DESKTOP_PATH, "algae_monitor_data.csv")
# 用來記錄上次讀取到哪裡的「書籤」檔案
BOOKMARK_FILE = os.path.join(DESKTOP_PATH, ".slicer_bookmark.txt")

# 感測器欄位定義 (需與 rpi_gui_monitor.py 同步)
SENSOR_KEYS = ["t", "ph", "tds", "ec", "turb", "lux", "c2b", "c2c"]
SENSOR_LABELS = {
    "t": "溫度", "ph": "酸鹼", "tds": "溶解", "ec": "導電",
    "turb": "濁度", "lux": "光照", "c2b": "CO2_B", "c2c": "CO2_C"
}
SENSOR_UNITS = {
    "t": "°C", "ph": "pH", "tds": "ppm", "ec": "mS/cm",
    "turb": "NTU", "lux": "lx", "c2b": "ppm", "c2c": "ppm"
}

def get_split_filename(timestamp_str):
    """根據數據的時間戳記決定 12 小時分段檔名，帶有時間範圍"""
    try:
        # 假設時間格式為 "2026-04-05 14:30:01"
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y%m%d")
        
        # 00:00~11:59 分到 0000-1159 檔；12:00~23:59 分到 1200-2359 檔
        if dt.hour < 12:
            time_range = "0000-1159"
        else:
            time_range = "1200-2359"
        
        return os.path.join(DESKTOP_PATH, f"split_{date_str}_{time_range}.csv")
    except ValueError as e:
        # 時間戳格式不正確
        print(f"⚠️ 警告: 無法解析時間戳 '{timestamp_str}' (格式錯誤)")
        print(f"   期望格式: YYYY-MM-DD HH:MM:SS (例如: 2026-04-11 14:30:01)")
        print(f"   錯誤詳情: {e}\n")
        return os.path.join(DESKTOP_PATH, "split_error_logs.csv")
    except Exception as e:
        # 其他異常
        print(f"❌ 錯誤: 處理時間戳 '{timestamp_str}' 時發生未知錯誤: {e}\n")
        return os.path.join(DESKTOP_PATH, "split_error_logs.csv")

def get_csv_header():
    """生成與 rpi_gui_monitor.py 相同格式的標題列"""
    header = ["時間", "裝置"]
    for key in SENSOR_KEYS:
        header.append(f"{SENSOR_LABELS[key]}({SENSOR_UNITS[key]})")
    return header

def main():
    print("=== 數據自動分流工具已啟動 ===")
    print(f"正在監控主檔案: {MAIN_CSV}")
    print("此程式會自動將主檔案的數據，每 12 小時備份一份到獨立的 CSV 中。")
    print("分段規則:")
    print("  • 00:00~11:59 → split_YYYYMMDD_0000-1159.csv")
    print("  • 12:00~23:59 → split_YYYYMMDD_1200-2359.csv\n")
    
    # 讀取上次處理到的位置
    last_pos = 0
    if os.path.exists(BOOKMARK_FILE):
        try:
            with open(BOOKMARK_FILE, 'r') as f:
                last_pos = int(f.read().strip())
        except:
            last_pos = 0

    while True:
        # 檢查主檔案是否存在
        if not os.path.exists(MAIN_CSV):
            time.sleep(5)
            continue
            
        current_size = os.path.getsize(MAIN_CSV)
        
        # 如果檔案縮小了（可能被手動刪除或清空），重置讀取位置
        if current_size < last_pos:
            last_pos = 0
            
        # 如果有新數據進來
        if current_size > last_pos:
            try:
                with open(MAIN_CSV, 'r', encoding='utf-8-sig') as f:
                    f.seek(last_pos)
                    reader = csv.reader(f)
                    
                    for row in reader:
                        # 跳過空行或標題列
                        if not row:
                            continue
                        
                        # 檢查是否為標題行（多種可能的格式）
                        first_cell = row[0].strip() if row else ""
                        if first_cell in ["時間", "Timestamp", "時間戳", "Date", "datetime"]:
                            continue
                            
                        # 確認該行至少有時間戳和裝置 ID (前兩欄)
                        if len(row) < 2:
                            print(f"⚠️ 警告: 數據行列數不足 (只有 {len(row)} 欄): {row}")
                            continue
                        
                        timestamp = row[0].strip()
                        device_id = row[1].strip()
                        
                        # 根據該行數據的時間戳記決定要存到哪個 12 小時檔案
                        target_file = get_split_filename(timestamp)
                        
                        # 寫入目標檔案
                        file_exists = os.path.exists(target_file)
                        with open(target_file, 'a', newline='', encoding='utf-8-sig') as out_f:
                            writer = csv.writer(out_f)
                            # 如果是新檔案，先寫入標題列
                            if not file_exists:
                                writer.writerow(get_csv_header())
                                print(f"✓ 新建檔案: {os.path.basename(target_file)}")
                            # 寫入完整行數據
                            writer.writerow(row)
                    
                    # 更新並儲存讀取位置
                    last_pos = f.tell()
                    with open(BOOKMARK_FILE, 'w') as bf:
                        bf.write(str(last_pos))
                        
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ 同步完成 | 主檔案: {current_size} bytes | 讀取位置: {last_pos}")
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 讀取時發生錯誤: {e}")
                    
        # 每 10 秒檢查一次主檔案
        time.sleep(10)

if __name__ == "__main__":
    main()