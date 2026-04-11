import serial
import serial.tools.list_ports
import json
import csv
import os
import threading
from datetime import datetime
import time

# --- 設定 ---
DESKTOP_PATH = os.path.expanduser("~/Desktop")
CSV_FILE = os.path.join(DESKTOP_PATH, "algae_monitor_data.csv")
BAUD_RATE = 9600 

# 感測器狀態控制 (預設全部開啟)
sensor_status = {
    "t": True,      # 溫度
    "ph": True,     # pH
    "tds": True,    # TDS
    "ec": True,     # EC
    "turb": True,   # 濁度
    "lux": True,    # 光照
    "c2b": True,    # CO2_B
    "c2c": True     # CO2_C
}

# 標籤對照表
labels = {
    "t": "溫度", "ph": "酸鹼 pH", "tds": "溶解 TDS", "ec": "導電 EC",
    "turb": "濁度", "lux": "光照", "c2b": "CO2_B", "c2c": "CO2_C"
}

# 初始化 CSV 標題
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Timestamp", "Device_ID", "Sensor", "Value"])

def handle_serial_port(port):
    """處理單個串口的數據讀取"""
    try:
        ser = serial.Serial(port, BAUD_RATE, timeout=2)
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        data = json.loads(line)
                        device_id = data.get("id", "Unknown")
                        v = data.get("v", {})
                        
                        # 過濾並顯示
                        display_data = []
                        print(f"\n[{timestamp}] 來自裝置: {device_id} ({port})")
                        print("-" * 50)
                        
                        for key, enabled in sensor_status.items():
                            if enabled and key in v:
                                val = v[key]
                                label = labels[key]
                                display_data.append(f"{label}: {val}")
                                
                                # 寫入 CSV (僅記錄開啟的感測器)
                                with open(CSV_FILE, mode='a', newline='') as file:
                                    writer = csv.writer(file)
                                    writer.writerow([timestamp, device_id, label, val])
                        
                        # 格式化顯示 (每行顯示兩個)
                        for i in range(0, len(display_data), 2):
                            row = display_data[i:i+2]
                            print(" | ".join(f"{item:<20}" for item in row))
                        
                        print("-" * 50)
                            
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"\nError on port {port}: {e}")

def menu_thread():
    """控制選單：手動切換感測器開關"""
    while True:
        print("\n" + "="*40)
        print(" [感測器開關控制選單]")
        for i, (key, enabled) in enumerate(sensor_status.items(), 1):
            status_str = "[ON]" if enabled else "[OFF]"
            print(f" {i}. {labels[key]:<10} {status_str}")
        print(" 9. 全部開啟")
        print(" 0. 全部關閉")
        print("="*40)
        
        choice = input("輸入編號切換狀態 (或輸入 Q 隱藏選單): ").upper()
        
        keys = list(sensor_status.keys())
        if choice == 'Q':
            print("選單已隱藏，數據持續更新中...")
            time.sleep(10)
            continue
        elif choice == '9':
            for k in sensor_status: sensor_status[k] = True
            print("--- 全部感測器已開啟 ---")
        elif choice == '0':
            for k in sensor_status: sensor_status[k] = False
            print("--- 全部感測器已關閉 ---")
        elif choice.isdigit() and 1 <= int(choice) <= len(keys):
            idx = int(choice) - 1
            key = keys[idx]
            sensor_status[key] = not sensor_status[key]
            print(f"--- {labels[key]} 已切換為 {'ON' if sensor_status[key] else 'OFF'} ---")
        else:
            print("!!! 無效輸入 !!!")
        time.sleep(1)

def main():
    ports = [p.device for p in serial.tools.list_ports.comports() if 'USB' in p.description or 'ACM' in p.device]
    if not ports:
        print("No USB serial devices found!")
        return
    print(f"Found ports: {ports}")
    
    # 啟動選單與串口執行緒
    threading.Thread(target=menu_thread, daemon=True).start()
    for port in ports:
        threading.Thread(target=handle_serial_port, args=(port,), daemon=True).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")

if __name__ == "__main__":
    main()
