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

def get_split_filename(timestamp_str):
    """根據數據的時間戳記決定 12 小時分段檔名"""
    try:
        # 假設時間格式為 "2026-04-05 14:30:01"
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        date_str = dt.strftime("%Y%m%d")
        # 00:00~11:59 分到 0000 檔；12:00~23:59 分到 1200 檔
        slot = "0000" if dt.hour < 12 else "1200"
        return os.path.join(DESKTOP_PATH, f"split_{date_str}_{slot}.csv")
    except:
        # 如果解析失敗，存到一個預設檔案
        return os.path.join(DESKTOP_PATH, "split_error_logs.csv")

def main():
    print("=== 數據自動分流工具已啟動 ===")
    print(f"正在監控主檔案: {MAIN_CSV}")
    print("此程式會自動將主檔案的數據，每 12 小時備份一份到獨立的 CSV 中。")
    
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
                with open(MAIN_CSV, 'r', encoding='utf-8') as f:
                    f.seek(last_pos)
                    reader = csv.reader(f)
                    
                    for row in reader:
                        # 跳過空行或標題列
                        if not row or row[0] == "Timestamp" or row[0] == "時間":
                            continue
                            
                        # 根據該行數據的時間戳記決定要存到哪個 12 小時檔案
                        target_file = get_split_filename(row[0])
                        
                        # 寫入目標檔案
                        file_exists = os.path.exists(target_file)
                        with open(target_file, 'a', newline='', encoding='utf-8-sig') as out_f:
                            writer = csv.writer(out_f)
                            if not file_exists:
                                writer.writerow(["時間", "裝置ID", "項目", "數值"])
                            writer.writerow(row)
                    
                    # 更新並儲存讀取位置
                    last_pos = f.tell()
                    with open(BOOKMARK_FILE, 'w') as bf:
                        bf.write(str(last_pos))
                        
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 數據同步中... 目前主檔案大小: {current_size} bytes")
            except Exception as e:
                print(f"讀取時發生錯誤: {e}")
                    
        # 每 10 秒檢查一次主檔案
        time.sleep(10)

if __name__ == "__main__":
    main()