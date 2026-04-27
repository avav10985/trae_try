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
  // 沒接時函式庫會回 -127 (DEVICE_DISCONNECTED_C);JSON 輸出 -1 標記斷線
  // 但 currentTemp 內部用 25 當預設值,避免 TDS/EC 溫補公式算出無意義數據
  sensors.requestTemperatures();
  float rawTemp = sensors.getTempCByIndex(0);
  bool tempOK = (rawTemp > -50 && rawTemp < 100);
  currentTemp = tempOK ? rawTemp : 25.0;
  v["t"] = tempOK ? rawTemp : -1;

  // 2. pH (兩點校準 + 斷線檢測)
  // 校準參數來自 PH_TwoPoint:V7=1.8629V (pH 7.00), V4=1.0223V (pH 4.00)
  // 有效電壓範圍 0.1~4.9V;範圍外 → -1 表示斷線/異常
  float phAvgADC = getAverageRead(PH_PIN);
  float phVoltage = phAvgADC * (5.0 / 1023.0);
  if (phVoltage < 0.1 || phVoltage > 4.9) {
    v["ph"] = -1;
  } else {
    v["ph"] = 3.5686 * phVoltage + 0.3519;
  }

  // 3. TDS (DFRobot 官方公式 + 溫度補償 + 校準係數 K + 斷線檢測)
  // K 來自 GravityTDS 校準程式 (cal:707, 707 ppm 標準液)
  // 有效電壓範圍 0.01~4.5V;範圍外 → -1
  // 注意:海水中此感測器會在 ~2.3V 飽和,讀值僅作趨勢用
  const float TDS_K = 0.60f;
  float tdsAvgADC = getAverageRead(TDS_PIN);
  float tdsVoltage = tdsAvgADC * (5.0 / 1023.0);
  if (tdsVoltage < 0.01 || tdsVoltage > 4.5) {
    v["tds"] = -1;
  } else {
    float compensationCoefficient = 1.0 + 0.02 * (currentTemp - 25.0);
    float compensationVolatge = tdsVoltage / compensationCoefficient;
    float tdsValue = (133.42 * pow(compensationVolatge, 3) - 255.86 * pow(compensationVolatge, 2) + 857.39 * compensationVolatge) * 0.5 * TDS_K;
    v["tds"] = (int)tdsValue;
  }

  // 4. EC (DFR0300-H 公式 + 溫度補償 + 校準係數 K + 斷線檢測, 單位 mS/cm)
  // K 來自 DFRobot_EC10 校準程式 (calec, 12.88 mS/cm 校準液)
  // 公式來自函式庫: rawEC = V_mV / 164 (RES2=820, ECREF=200)
  // 有效電壓範圍 0.05~5.0V;ADC < 5 → -1(海水可能在 5V 附近飽和,允許上限)
  const float EC_K = 0.85f;
  float ecAvgADC = getAverageRead(EC_PIN);
  if (ecAvgADC < 5) {
    v["ec"] = -1;
  } else {
    float ecVoltage_mV = ecAvgADC * (5000.0 / 1023.0);
    float ecRaw = ecVoltage_mV / 164.0;
    float ecTempCoeff = 1.0 + 0.0185 * (currentTemp - 25.0);
    v["ec"] = ecRaw * EC_K / ecTempCoeff;
  }

  // 5. 濁度 (SEN0189, 單位 NTU + 斷線檢測)
  // DFRobot 官方公式: NTU = -1120.4*V² + 5742.3*V - 4352.9
  // 正常輸出範圍 2.5~4.5V;超出 1.0~4.95V 視為斷線(SEN0189 不會輸出 < 1V)
  // 4.2~4.95V 視為清水(0 NTU);1.0~2.5V 視為飽和(3000 NTU)
  // 注意:模組上的 A/D 切換開關必須打到 A(類比模式)
  float turbAvgADC = getAverageRead(TURBIDITY_PIN);
  float turbVoltage = turbAvgADC * (5.0 / 1023.0);
  float turbNTU;
  if (turbVoltage < 1.0 || turbVoltage > 4.95) turbNTU = -1;
  else if (turbVoltage > 4.2)                   turbNTU = 0;
  else if (turbVoltage < 2.5)                   turbNTU = 3000;
  else turbNTU = -1120.4 * turbVoltage * turbVoltage + 5742.3 * turbVoltage - 4352.9;
  v["turb"] = turbNTU;

  // 6. 光照 (BH1750)
  // 函式庫在 I2C 異常時回負值;範圍外也視為斷線
  float lux = lightMeter.readLightLevel();
  v["lux"] = (lux < 0 || lux > 100000) ? -1 : lux;

  // 7. CO2 (交替讀取 MH-Z19B & C)
  v["c2b"] = readCO2(co2SerialB);
  delay(100);
  v["c2c"] = readCO2(co2SerialC);

  // 輸出 JSON 到 Serial
  serializeJson(doc, Serial);
  Serial.println();

  delay(10000); // --- 優化：改為每 10 秒鐘傳送一次，適合長期監測 ---
}
