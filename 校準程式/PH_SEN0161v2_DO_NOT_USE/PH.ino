#include "DFRobot_PH.h"
#include <EEPROM.h>
#include <OneWire.h>
#include <DallasTemperature.h>

/*
 * 這是 DFRobot Gravity: 類比 pH 感測器 V2 的校準程式。
 * 序列埠指令：
 * enterph -> 進入校準模式
 * calph   -> 在標準液中校準（自動識別 4.0 或 7.0）
 * exitph  -> 儲存並退出
 */

#define PH_PIN A2
#define DS18B20_PIN 2 // 你的溫度感測器接在 D2

OneWire oneWire(DS18B20_PIN);
DallasTemperature sensors(&oneWire);

float voltage, phValue, temperature = 25;
DFRobot_PH ph;

void setup()
{
    Serial.begin(9600);  
    sensors.begin(); // 初始化溫度感測器
    ph.begin();      // 初始化 pH 模組
}

void loop()
{
    static unsigned long timepoint = millis();
    if(millis() - timepoint > 1000U){                  // 時間間隔：1秒
        timepoint = millis();
        
        // 讀取溫度感測器以執行自動溫度補償
        temperature = readTemperature();         
        
        // 讀取類比電壓 (轉換為 mV)
        voltage = analogRead(PH_PIN) / 1024.0 * 5000;  
        
        // 將電壓轉換為 pH 值（包含溫度補償）
        phValue = ph.readPH(voltage, temperature);  
        
        Serial.print("溫度:");
        Serial.print(temperature, 1);
        Serial.print("^C  pH值:");
        Serial.println(phValue, 2);
    }
    // 持續監聽序列埠指令
    ph.calibration(voltage, temperature);           
}

float readTemperature()
{
    sensors.requestTemperatures();
    float t = sensors.getTempCByIndex(0);
    // 如果讀取失敗 (例如感測器斷線回傳 -127)，則回傳預設值 25.0
    if (t == -127.00) return 25.0; 
    return t;
}