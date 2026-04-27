#include <EEPROM.h>
#include "GravityTDS.h"
#include <OneWire.h>
#include <DallasTemperature.h>

/*********** 注意事項與故障排除 ***************
 1. 此程式碼已在 Arduino Uno 上通過測試。
 2. 校準指令 (在序列埠監視器輸入)：
      enter          -> 進入校準模式
      cal:tds value  -> 使用已知的 TDS 值校準 (25°C 環境)。例如：cal:707
      exit           -> 儲存參數並退出校準模式
 ****************************************************/

#define TdsSensorPin A0
#define DS18B20_PIN 2 // 你的溫度感測器接在 D2

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

GravityTDS gravityTds;

float temperature = 0, tdsValue = 0;

void setup()
{
    Serial.begin(115200);
    sensors.begin();      // 初始化溫度感測器
    gravityTds.setPin(TdsSensorPin);
    gravityTds.setAref(5.0);  // ADC 參考電壓，Arduino UNO 預設為 5.0V
    gravityTds.setAdcRange(1024);  // 10bit ADC 為 1024
    gravityTds.begin();  // 初始化 TDS 模組
}

void loop()
{
    // 讀取溫度感測器並進行溫度補償
    temperature = readTemperature();  
    
    gravityTds.setTemperature(temperature);  // 設定當前溫度以執行溫度補償
    gravityTds.update();  // 進行取樣與計算
    tdsValue = gravityTds.getTdsValue();  // 獲取 TDS 數值
    
    Serial.print(temperature, 0);
    Serial.print("度  ");
    Serial.print(tdsValue, 0);
    Serial.println("ppm");
    delay(1000);
}

float readTemperature()
{
    sensors.requestTemperatures();
    float t = sensors.getTempCByIndex(0);
    // 如果讀取失敗 (例如感測器斷線回傳 -127)，則回傳預設值 25.0
    if (t == -127.00) return 0; 
    return t;
}