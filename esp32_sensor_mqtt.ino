#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <BH1750.h>

// --- Wi-Fi 設定 ---
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// --- Raspberry Pi (MQTT Broker) 設定 ---
const char* mqtt_server = "192.168.1.xxx"; // 請填入 RPi 的固定 IP 地址
const char* mqtt_topic = "sensor/data";

WiFiClient espClient;
PubSubClient client(espClient);

// --- 感測器腳位與實例定義 ---

// 1. DS18B20 (防水溫度) - Digital Pin 4
const int ONE_WIRE_BUS = 4;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// 2. Analog 感測器 (ADC1 Pins - 32, 33, 34, 35)
const int TDS_PIN = 32;
const int EC_PIN = 33;
const int PH_PIN = 34;
const int TURBIDITY_PIN = 35;

// 3. BH1750 (光照) - I2C (SDA 21, SCL 22)
BH1750 lightMeter;

// 4. MH-Z19B & C (CO2) - 使用 Hardware Serial
HardwareSerial serialB(1); // UART1
HardwareSerial serialC(2); // UART2
// MH-Z19B Pins: RX=14, TX=13
// MH-Z19C Pins: RX=16, TX=17

// --- 全域變數用於補償 ---
float currentTemp = 25.0; // 預設溫度

void setup_wifi() {
  delay(10);
  Serial.println("\nConnecting to WiFi...");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_Algae_Monitor")) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      delay(5000);
    }
  }
}

// 讀取 MH-Z19 數據的函式
int readCO2(HardwareSerial &n_serial) {
  byte cmd[9] = {0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79};
  byte response[9];
  n_serial.write(cmd, 9);
  memset(response, 0, 9);
  n_serial.readBytes(response, 9);
  
  if (response[0] != 0xFF || response[1] != 0x86) return -1;
  
  byte crc = 0;
  for (int i = 1; i < 8; i++) crc += response[i];
  crc = 255 - crc + 1;
  
  if (response[8] != crc) return -1;
  return (response[2] << 8) + response[3];
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);

  // 初始化感測器
  sensors.begin();
  Wire.begin();
  lightMeter.begin();
  
  // 初始化 UART 給 CO2 感測器
  serialB.begin(9600, SERIAL_8N1, 14, 13); // RX, TX
  serialC.begin(9600, SERIAL_8N1, 16, 17); // RX, TX

  pinMode(TDS_PIN, INPUT);
  pinMode(EC_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  StaticJsonDocument<1024> doc;
  doc["device_id"] = "ESP32_ALGAE_01";
  JsonObject vals = doc.createNestedObject("values");

  // 1. 讀取溫度 (DS18B20)
  sensors.requestTemperatures();
  currentTemp = sensors.getTempCByIndex(0);
  vals["temperature"] = currentTemp;

  // 2. 讀取 pH (Analog) - 需根據 V2 公式校準
  float phVoltage = analogRead(PH_PIN) * (3.3 / 4095.0);
  // 簡化公式: pH = 7 + (V_neutral - V) / Slope
  vals["ph"] = 3.5 * phVoltage; // 這裡需根據校準液調整系數

  // 3. 讀取 TDS (Analog) - 需溫度補償
  float tdsVoltage = analogRead(TDS_PIN) * (3.3 / 4095.0);
  float compensationCoefficient = 1.0 + 0.02 * (currentTemp - 25.0);
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  float tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5;
  vals["tds"] = tdsValue;

  // 4. 讀取 EC (Analog)
  float ecVoltage = analogRead(EC_PIN) * (3.3 / 4095.0);
  vals["ec"] = ecVoltage * 1000; // 簡化展示，需校準

  // 5. 讀取濁度 (Turbidity)
  float turbVoltage = analogRead(TURBIDITY_PIN) * (3.3 / 4095.0);
  vals["turbidity"] = turbVoltage;

  // 6. 讀光照 (BH1750)
  vals["lux"] = lightMeter.readLightLevel();

  // 7. 讀 CO2 (MH-Z19B & C)
  vals["co2_b"] = readCO2(serialB);
  vals["co2_c"] = readCO2(serialC);

  // 轉換成 JSON 並發送
  char buffer[1024];
  serializeJson(doc, buffer);
  client.publish(mqtt_topic, buffer);
  
  Serial.print("Published: ");
  Serial.println(buffer);

  delay(10000); // 每 10 秒傳送一次
}
