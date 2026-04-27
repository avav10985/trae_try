/*
 * PH EEPROM 重置程式
 *
 * 用途：清除先前用 DFRobot_PH 函式庫（SEN0161-v2 校準程式）寫入 UNO EEPROM 的
 *       pH 校準值，恢復成函式庫的出廠預設值。
 *
 * 使用方式：
 *   1. 將此 .ino 燒錄到 UNO
 *   2. 開啟序列埠監視器（鮑率 9600）
 *   3. 觀察印出的「重置前」與「重置後」電壓值
 *   4. 看到 "DONE" 即完成，可重新燒錄你的主程式
 *
 * EEPROM 配置（DFRobot_PH v1.x）：
 *   位址 0x00 (4 bytes float) -> neutralVoltage  預設 1500.00 mV (pH 7)
 *   位址 0x04 (4 bytes float) -> acidVoltage     預設 2032.44 mV (pH 4)
 */

#include <EEPROM.h>

#define PH_EEPROM_ADDR        0x00
#define DEFAULT_NEUTRAL_MV    1500.00f
#define DEFAULT_ACID_MV       2032.44f

void printStored(const char* tag) {
  float neutral, acid;
  EEPROM.get(PH_EEPROM_ADDR, neutral);
  EEPROM.get(PH_EEPROM_ADDR + sizeof(float), acid);
  Serial.print(tag);
  Serial.print(" neutralVoltage(pH7) = ");
  Serial.print(neutral, 2);
  Serial.print(" mV,  acidVoltage(pH4) = ");
  Serial.print(acid, 2);
  Serial.println(" mV");
}

void setup() {
  Serial.begin(9600);
  while (!Serial) { ; }
  delay(200);

  Serial.println();
  Serial.println("=== PH EEPROM Reset ===");

  printStored("[BEFORE]");

  float neutral = DEFAULT_NEUTRAL_MV;
  float acid    = DEFAULT_ACID_MV;
  EEPROM.put(PH_EEPROM_ADDR, neutral);
  EEPROM.put(PH_EEPROM_ADDR + sizeof(float), acid);

  printStored("[AFTER ]");

  Serial.println("DONE. EEPROM 已恢復為 DFRobot_PH 預設值。");
  Serial.println("現在可以重新燒錄你的主程式。");
}

void loop() {
}
