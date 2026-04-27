#include <OneWire.h>
#include <DallasTemperature.h>
#include "DFRobot_EC10.h"
#include <EEPROM.h>

#define EC_PIN A1
#define DS18B20_PIN 2 // 你的溫度感測器接在 D2

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

float voltage, ecValue, temperature = 25; // 預設溫度為 25 度
DFRobot_EC10 ec;

void setup()
{
  Serial.begin(9600);  
  sensors.begin(); // 啟動溫度感測器
  ec.begin();      // 初始化 EC 模組，會從 EEPROM 讀取之前的校準數據
}

void loop()
{
    static unsigned long timepoint = millis();
    if(millis() - timepoint > 1000U)  // 每隔 1 秒執行一次
    {
      timepoint = millis();
      // 讀取溫度感測器以執行溫度補償
      temperature = readTemperature(); 
      
      // 將類比數值轉換為毫伏特 (mV)
      voltage = analogRead(EC_PIN) / 1024.0 * 5000;  
      
      Serial.print("電壓:");
      Serial.print(voltage);
      
      // 根據電壓與溫度計算出電導度 (EC)
      ecValue = ec.readEC(voltage, temperature);  
      
      Serial.print("  溫度:");
      Serial.print(temperature, 1);
      Serial.print("^C  EC值:");
      Serial.print(ecValue, 1);
      Serial.println(" ms/cm");
    }
    // 持續監聽序列埠指令，以便進行校準程序
    ec.calibration(voltage, temperature);  
}

float readTemperature()
{
  sensors.requestTemperatures();
  float t = sensors.getTempCByIndex(0);
  if (t == -127.00) return 0; // 如果讀取失敗回傳預設值
  return t;
}