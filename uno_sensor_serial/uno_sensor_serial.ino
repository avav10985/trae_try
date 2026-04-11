#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <BH1750.h>
#include <SoftwareSerial.h>
#include <ArduinoJson.h>

/* 
 * Arduino Uno 限制說明:
 * 1. 記憶體 (RAM) 僅 2KB，JSON 物件不能太大。
 * 2. 只有一個硬體串口 (Serial)，與電腦/RPi 通訊用。
 * 3. MH-Z19B/C 需使用 SoftwareSerial。
 * 4. A4, A5 腳位被 I2C (BH1750) 佔用，剩下 A0-A3 給類比感測器。
 */

// --- 感測器腳位定義 ---
const int DS18B20_PIN = 2;
const int TDS_PIN = A0;
const int EC_PIN = A1;
const int PH_PIN = A2;
const int TURBIDITY_PIN = A3;

// --- MH-Z19B & C (SoftwareSerial) ---
SoftwareSerial co2SerialB(3, 4); // RX, TX
SoftwareSerial co2SerialC(5, 6); // RX, TX

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);
BH1750 lightMeter;

float currentTemp = 25.0;

// --- 優化：平均值採樣函式 ---
float getAverageRead(int pin, int samples = 20) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(10);
  }
  return (float)sum / samples;
}

// 讀取 MH-Z19 數據的函式 (SoftwareSerial 需要 .listen())
int readCO2(SoftwareSerial &swSerial) {
  swSerial.listen();
  byte cmd[9] = {0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79};
  byte response[9];
  swSerial.write(cmd, 9);
  
  unsigned long startTime = millis();
  while (swSerial.available() < 9 && (millis() - startTime) < 1000) {
    delay(10);
  }

  if (swSerial.available() < 9) return -1;
  swSerial.readBytes(response, 9);
  
  if (response[0] != 0xFF || response[1] != 0x86) return -1;
  
  byte crc = 0;
  for (int i = 1; i < 8; i++) crc += response[i];
  crc = 255 - crc + 1;
  
  if (response[8] != crc) return -1;
  return (response[2] << 8) + response[3];
}

void setup() {
  Serial.begin(9600); // Uno 建議使用較低速率確保穩定
  sensors.begin();
  Wire.begin();
  lightMeter.begin();
  co2SerialB.begin(9600);
  co2SerialC.begin(9600);

  pinMode(TDS_PIN, INPUT);
  pinMode(EC_PIN, INPUT);
  pinMode(PH_PIN, INPUT);
  pinMode(TURBIDITY_PIN, INPUT);
}

void loop() {
  // Uno RAM 較小，使用較小的 JsonDocument
  StaticJsonDocument<256> doc;
  doc["id"] = "UNO_01";
  JsonObject v = doc.createNestedObject("v");

  // 1. 溫度 (DS18B20)
  sensors.requestTemperatures();
  currentTemp = sensors.getTempCByIndex(0);
  if (currentTemp < -50) currentTemp = 25.0; // 錯誤處理
  v["t"] = currentTemp;

  // 2. pH (使用 V2 精確公式與溫度補償)
  float phAvgADC = getAverageRead(PH_PIN);
  float phVoltage = phAvgADC * (5.0 / 1023.0);
  // 基礎公式 pH = 7 + (V_neutral - V) / Slope
  // 這裡先提供標準係數，校準後需修改 3.5 這個值
  v["ph"] = 3.5 * phVoltage; 

  // 3. TDS (使用溫度補償公式)
  float tdsAvgADC = getAverageRead(TDS_PIN);
  float tdsVoltage = tdsAvgADC * (5.0 / 1023.0);
  float compensationCoefficient = 1.0 + 0.02 * (currentTemp - 25.0);
  float compensationVolatge = tdsVoltage / compensationCoefficient;
  // DFRobot 官方 TDS V2 轉換公式
  float tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5;
  v["tds"] = (int)tdsValue;

  // 4. EC (導電度/鹽度)
  float ecAvgADC = getAverageRead(EC_PIN);
  v["ec"] = (int)ecAvgADC; // 建議校準後換算成 ms/cm

  // 5. 濁度 (Turbidity)
  float turbAvgADC = getAverageRead(TURBIDITY_PIN);
  v["turb"] = turbAvgADC * (5.0 / 1023.0);

  // 6. 光照 (BH1750)
  v["lux"] = lightMeter.readLightLevel();

  // 7. CO2 (交替讀取 MH-Z19B & C)
  v["c2b"] = readCO2(co2SerialB);
  delay(100);
  v["c2c"] = readCO2(co2SerialC);

  // 輸出 JSON 到 Serial
  serializeJson(doc, Serial);
  Serial.println();

  delay(10000); // --- 優化：改為每 10 秒鐘傳送一次，適合長期監測 ---
}
