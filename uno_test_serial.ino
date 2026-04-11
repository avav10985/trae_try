#include <ArduinoJson.h>

void setup() {
  // 設定與樹莓派通訊的速率 (與 ESP32 相同)
  Serial.begin(9600);
  while (!Serial) continue; 
  
  Serial.println("--- Uno Test Mode Started ---");
}

void loop() {
  // Uno RAM 較小，使用較小的 JsonDocument
  StaticJsonDocument<256> doc;
  doc["id"] = "UNO_TEST";
  
  JsonObject v = doc.createNestedObject("v");
  v["t"] = 24.8 + (random(-5, 6) / 10.0);      // 模擬溫度
  v["ph"] = 6.8 + (random(-3, 4) / 10.0);      // 模擬 pH
  v["tds"] = 430 + random(-10, 11);            // 模擬 TDS
  v["ec"] = 1100 + random(-30, 31);            // 模擬 EC
  v["turb"] = 1.2 + (random(-1, 2) / 10.0);    // 模擬濁度
  v["lux"] = 450 + random(-50, 51);            // 模擬光照
  v["c2b"] = 380 + random(0, 50);              // 模擬 CO2 B
  v["c2c"] = 390 + random(0, 50);              // 模擬 CO2 C

  // 輸出 JSON 到 Serial
  serializeJson(doc, Serial);
  Serial.println(); // 換行作為結束符號

  delay(3000); // 每 3 秒傳送一次
}
