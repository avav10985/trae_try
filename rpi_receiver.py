import paho.mqtt.client as mqtt
import json
import csv
import os
from datetime import datetime

# --- MQTT 設定 ---
MQTT_BROKER = "localhost"
MQTT_TOPIC = "sensor/data"

# --- CSV 記錄檔設定 ---
DESKTOP_PATH = os.path.expanduser("~/Desktop")
CSV_FILE = os.path.join(DESKTOP_PATH, "algae_monitor_data.csv")

# 如果檔案不存在，先建立標題列
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp", "Device_ID", "Temp_C", "pH", 
            "TDS_ppm", "EC_ms", "Turbidity_V", "Lux", 
            "CO2_B_ppm", "CO2_C_ppm"
        ])

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        device_id = data.get("device_id", "unknown")
        vals = data.get("values", {})
        
        # 提取各項數值
        temp = vals.get("temperature", 0)
        ph = vals.get("ph", 0)
        tds = vals.get("tds", 0)
        ec = vals.get("ec", 0)
        turb = vals.get("turbidity", 0)
        lux = vals.get("lux", 0)
        co2_b = vals.get("co2_b", 0)
        co2_c = vals.get("co2_c", 0)

        print(f"[{timestamp}] Data received from {device_id}")
        print(f"  Temp: {temp}°C, pH: {ph}, TDS: {tds}, Lux: {lux}")

        # 寫入 CSV
        with open(CSV_FILE, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                timestamp, device_id, temp, ph, 
                tds, ec, turb, lux, 
                co2_b, co2_c
            ])
                
    except Exception as e:
        print(f"Error processing message: {e}")

# 初始化 MQTT Client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    print(f"Starting Algae Monitor Receiver...")
    print(f"Connecting to broker: {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopping...")
    client.disconnect()
except Exception as e:
    print(f"Failed to run receiver: {e}")
