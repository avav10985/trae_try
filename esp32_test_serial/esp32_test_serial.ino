#include <ArduinoJson.h>

void setup() {
  // 設定與樹莓派通訊的速率
  Serial.begin(9600);
  while (!Serial) continue; // 等待串口準備好
  
  Serial.println("--- ESP32 Test Mode Started ---");
}

void loop() {
  // 建立模擬數據的 JSON
  StaticJsonDocument<512> doc;
  doc["id"] = "ESP32_TEST";
  
  JsonObject v = doc.createNestedObject("v");
  v["t"] = 25.5 + (random(-10, 11) / 10.0);    // 模擬溫度
  v["ph"] = 7.0 + (random(-5, 6) / 10.0);      // 模擬 pH
  v["tds"] = 450 + random(-20, 21);            // 模擬 TDS
  v["ec"] = 1200 + random(-50, 51);            // 模擬 EC
  v["turb"] = 1.5 + (random(-2, 3) / 10.0);    // 模擬濁度
  v["lux"] = 500 + random(-100, 101);          // 模擬光照
  v["c2b"] = 400 + random(0, 100);             // 模擬 CO2 B
  v["c2c"] = 410 + random(0, 100);             // 模擬 CO2 C

  // 輸出 JSON 到 Serial
  serializeJson(doc, Serial);
  Serial.println(); // 換行作為結束符號

  delay(3000); // 每 3 秒傳送一次，方便觀察
}
