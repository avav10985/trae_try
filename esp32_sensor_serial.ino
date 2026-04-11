#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <BH1750.h>
#include <ArduinoJson.h>

/* 
 * ESP32 Lolin Serial 版本說明:
 * 1. 透過 USB 數據線與樹莓派通訊 (Baud rate: 9600)。
 * 2. 包含數位濾波、溫度補償與精確公式。
 * 3. 數據格式符合桌面 GUI 監測系統需求。
 */

// --- 腳位定義 ---
const int DS18B20_PIN = 4;
const int TDS_PIN = 32;
const int EC_PIN = 33;
const int PH_PIN = 34;
const int TURBIDITY_PIN = 35;

// --- MH-Z19B & C ---
HardwareSerial serialB(1); // UART1
HardwareSerial serialC(2); // UART2
// MH-Z19B Pins: RX=14, TX=13
// MH-Z19C Pins: RX=16, TX=17

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);
BH1750 lightMeter;

float currentTemp = 25.0;

// --- 數位濾波：平均值採樣函式 ---
float getAverageRead(int pin, int samples = 20) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(5);
  }
  return (float)sum / samples;
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
  // 設定與樹莓派通訊的速率
  Serial.begin(9600);
  
  // 初始化感測器
  sensors.begin();
  Wire.begin(21, 22); // SDA, SCL
  lightMeter.begin();
  
  // 初始化 UART 給 CO2 感測器
  serialB.begin(9600, SERIAL_8N1, 14, 13); // RX, TX
  serialC.begin(9600, SERIAL_8N1, 16, 17); // RX, TX

  pinMode(TDS_PIN, INPUT);
  pinMode(EC_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
  
  Serial.println("--- ESP32 Serial Monitor Started ---");
}

void loop() {
  StaticJsonDocument<512> doc;
  doc["id"] = "ESP32_01";
  JsonObject v = doc.createNestedObject("v");

  // 1. 讀取溫度 (DS18B20)
  sensors.requestTemperatures();
  currentTemp = sensors.getTempCByIndex(0);
  if (currentTemp < -50) currentTemp = 25.0; // 錯誤處理
  v["t"] = currentTemp;

  // 2. 讀取 pH (使用平均採樣與補償)
  float phAvgADC = getAverageRead(PH_PIN);
  float phVoltage = phAvgADC * (3.3 / 4095.0);
  v["ph"] = phVoltage * 3.5; // 這裡需根據校準液調整係數

  // 3. 讀取 TDS (含溫度補償公式)
  float tdsAvgADC = getAverageRead(TDS_PIN);
  float tdsVoltage = tdsAvgADC * (3.3 / 4095.0);
  float compensationCoefficient = 1.0 + 0.02 * (currentTemp - 25.0);
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  float tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5;
  v["tds"] = (int)tdsValue;

  // 4. 讀取 EC & 濁度
  v["ec"] = (int)getAverageRead(EC_PIN);
  v["turb"] = getAverageRead(TURBIDITY_PIN) * (3.3 / 4095.0);

  // 5. 讀取光照 (BH1750)
  v["lux"] = lightMeter.readLightLevel();

  // 6. 讀取 CO2 (MH-Z19B & C)
  v["c2b"] = readCO2(serialB);
  v["c2c"] = readCO2(serialC);

  // 輸出符合 GUI 格式的 JSON 到 Serial
  serializeJson(doc, Serial);
  Serial.println(); 

  delay(10000); // 每 10 秒傳送一次
}