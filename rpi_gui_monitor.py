import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import csv
import os
import threading
from datetime import datetime
import time
import requests  # 需安裝: pip3 install requests

# --- 設定 ---
DESKTOP_PATH = os.path.expanduser("~/Desktop")
CSV_FILE = os.path.join(DESKTOP_PATH, "algae_monitor_data.csv")
BAUD_RATE = 9600
BUFFER_SIZE = 20  # 每累積 20 筆數據寫入一次 SD 卡
FLUSH_INTERVAL = 60  # 即使數據不夠，每 60 秒也強制寫入一次

# 請貼上你的 Google Apps Script 網址
CLOUD_URL = "https://script.google.com/macros/s/[REDACTED-APPS-SCRIPT-ID]/exec"

class AlgaeMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("藻類比賽 - 數據監測儀表板 (SD卡保護版)")
        self.root.geometry("800x600")
        
        # 感測器狀態與標籤
        self.sensor_keys = ["t", "ph", "tds", "ec", "turb", "lux", "c2b", "c2c"]
        self.labels = {
            "t": "溫度 (°C)", "ph": "酸鹼 (pH)", "tds": "溶解 (ppm)", "ec": "導電 (mS/cm)",
            "turb": "濁度 (V)", "lux": "光照 (lx)", "c2b": "CO2_B (ppm)", "c2c": "CO2_C (ppm)"
        }
        self.status = {key: tk.BooleanVar(value=True) for key in self.sensor_keys}
        self.data_vars = {key: tk.StringVar(value="---") for key in self.sensor_keys}
        self.cloud_sync = tk.BooleanVar(value=False) # 預設關閉雲端同步
        
        # 緩衝區與鎖
        self.data_buffer = []
        self.buffer_lock = threading.Lock()
        self.last_flush_time = time.time()
        
        self.setup_ui()
        self.start_serial_threads()
        self.start_timer_thread()
        
        # 初始化 CSV
        if not os.path.exists(CSV_FILE):
            with open(CSV_FILE, mode='w', newline='') as f:
                header = ["Timestamp", "Device", "Temp", "pH", "TDS", "EC", "Turb", "Lux", "CO2_B", "CO2_C"]
                csv.writer(f).writerow(header)

    def setup_ui(self):
        header = tk.Label(self.root, text="藻類監測系統", font=("Arial", 24, "bold"))
        header.pack(pady=10)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20)

        display_frame = tk.LabelFrame(main_frame, text="即時數據", font=("Arial", 14))
        display_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        for key in self.sensor_keys:
            frame = tk.Frame(display_frame)
            frame.pack(fill="x", pady=5, padx=10)
            tk.Label(frame, text=self.labels[key], font=("Arial", 12), width=15, anchor="w").pack(side="left")
            tk.Label(frame, textvariable=self.data_vars[key], font=("Arial", 14, "bold"), fg="blue").pack(side="left")

        control_frame = tk.LabelFrame(main_frame, text="監控開關 (勾選以記錄)", font=("Arial", 14))
        control_frame.pack(side="right", fill="y", padx=10, pady=10)

        for key in self.sensor_keys:
            tk.Checkbutton(control_frame, text=self.labels[key], variable=self.status[key], font=("Arial", 11)).pack(anchor="w", pady=2, padx=10)

        tk.Label(control_frame, text="--- 雲端設定 ---", font=("Arial", 12, "bold")).pack(pady=10)
        tk.Checkbutton(control_frame, text="同步至 Google Sheets", variable=self.cloud_sync, font=("Arial", 11), fg="green").pack(anchor="w", padx=10)

        self.status_bar = tk.Label(self.root, text="正在搜尋裝置...", bd=1, relief="sunken", anchor="w")
        self.status_bar.pack(side="bottom", fill="x")

    def save_to_buffer(self, timestamp, device_id, values_dict):
        """將整行數據存入緩衝區 (水平模式)"""
        with self.buffer_lock:
            # 依照順序排列：t, ph, tds, ec, turb, lux, c2b, c2c
            row = [timestamp, device_id]
            for key in self.sensor_keys:
                # 如果該感測器沒開啟，填入 "N/A"
                if self.status[key].get():
                    row.append(values_dict.get(key, "---"))
                else:
                    row.append("OFF")
            
            self.data_buffer.append(row)
            if len(self.data_buffer) >= BUFFER_SIZE:
                self.flush_buffer()

    def flush_buffer(self):
        """強制將緩衝區數據寫入 SD 卡"""
        if not self.data_buffer:
            return
        try:
            with open(CSV_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerows(self.data_buffer)
            self.data_buffer = []
            self.last_flush_time = time.time()
            self.status_bar.config(text=f"數據已同步至 SD 卡: {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            self.status_bar.config(text=f"寫入失敗: {e}")

    def start_timer_thread(self):
        """定時器：確保即使數據不夠，也會定期存檔"""
        def timer_loop():
            while True:
                time.sleep(10) # 每 10 秒檢查一次
                if time.time() - self.last_flush_time >= FLUSH_INTERVAL:
                    with self.buffer_lock:
                        self.flush_buffer()
        threading.Thread(target=timer_loop, daemon=True).start()

    def sync_to_cloud(self, device_id, values_dict):
        """背景傳送完整數據包到 Google Sheets"""
        if not self.cloud_sync.get() or CLOUD_URL == "YOUR_GOOGLE_SCRIPT_URL_HERE":
            return
            
        def task():
            try:
                # 準備傳送給 GAS 的資料格式，Key 需與 GAS 對應
                payload = {
                    "device_id": device_id,
                    "temp": values_dict.get("t"),
                    "ph": values_dict.get("ph"),
                    "tds": values_dict.get("tds"),
                    "ec": values_dict.get("ec"),
                    "turb": values_dict.get("turb"),
                    "lux": values_dict.get("lux"),
                    "co2b": values_dict.get("c2b"),
                    "co2c": values_dict.get("c2c")
                }
                # 傳送 POST 請求
                response = requests.post(CLOUD_URL, json=payload, timeout=5)
                if response.status_code != 200:
                    print(f"雲端同步失敗: {response.status_code}")
            except Exception as e:
                print(f"網路連線錯誤: {e}")
                
        # 使用執行緒背景執行，不影響即時監控
        threading.Thread(target=task, daemon=True).start()

    def handle_serial(self, port):
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=1)
            self.status_bar.config(text=f"已連接: {port}")
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        try:
                            data = json.loads(line)
                            v = data.get("v", {})
                            device_id = data.get("id", "Unknown")
                            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            # 更新 UI 顯示
                            for key in self.sensor_keys:
                                if key in v:
                                    if self.status[key].get():
                                        self.data_vars[key].set(f"{v[key]}")
                                    else:
                                        self.data_vars[key].set("已關閉")
                            
                            # 一次性存入 Buffer 並上傳雲端 (整組數據打包)
                            self.save_to_buffer(ts, device_id, v)
                            self.sync_to_cloud(device_id, v)
                        except Exception as e:
                            print(f"解析錯誤: {e}")
        except Exception as e:
            self.status_bar.config(text=f"錯誤: {port} 已斷開")

    def start_serial_threads(self):
        ports = [p.device for p in serial.tools.list_ports.comports() if 'USB' in p.description or 'ACM' in p.device]
        if not ports:
            messagebox.showwarning("警告", "找不到任何 USB 裝置！請檢查連線。")
            return
        for port in ports:
            threading.Thread(target=self.handle_serial, args=(port,), daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = AlgaeMonitorApp(root)
    root.mainloop()
