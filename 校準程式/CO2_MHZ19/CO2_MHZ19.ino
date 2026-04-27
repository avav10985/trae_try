/*
 * MH-Z19B / MH-Z19C CO2 感測器校準程式
 *
 * 適用情境:藻類監測屬於密閉/低 CO2 環境,感測器長期看不到 400 ppm 基準,
 * ABC 自動校準會錯誤地把長期最低點當成 400 ppm,造成讀值持續漂移。
 *
 * 建議流程:
 *   1. 把兩顆感測器都拿到戶外通風處,放 >= 20 分鐘讓讀值穩定
 *   2. 燒錄此程式 → 開序列埠監視器(鮑率 9600,行尾選 Newline)
 *   3. 輸入 abcoff  → 兩顆都關閉 ABC
 *   4. 輸入 zerob   → B 感測器歸零(設為 400 ppm)
 *   5. 輸入 zeroc   → C 感測器歸零
 *   6. 輸入 read 觀察讀值,應該都接近 400 ppm
 *   7. 重新燒錄主程式,放回藻類池
 *   8. 之後每月找晴天重做一次
 *
 * 接線(與主程式 uno_sensor_serial.ino 相同):
 *   MH-Z19 B: TX -> Arduino D3, RX -> Arduino D4
 *   MH-Z19 C: TX -> Arduino D5, RX -> Arduino D6
 *   兩顆都接 5V / GND
 *
 * 指令列表(全部小寫):
 *   read     -> 立即讀取兩顆 CO2 數值
 *   zerob    -> 對 B 送歸零指令
 *   zeroc    -> 對 C 送歸零指令
 *   abcoff   -> 兩顆都關閉 ABC
 *   abcon    -> 兩顆都打開 ABC(若想恢復出廠設定)
 *   help     -> 顯示指令說明
 *
 * 注意:
 *   - 歸零必須在已知 400 ppm 環境(戶外通風 >= 20 分鐘)
 *   - 部分 MH-Z19 版本關 ABC 需重新上電才生效,建議下完 abcoff 後拔電再插
 *   - 歸零指令送出後約 1 分鐘讀值才會穩定到 400 ppm
 */

#include <SoftwareSerial.h>

SoftwareSerial co2SerialB(3, 4);  // RX, TX
SoftwareSerial co2SerialC(5, 6);

const byte CMD_READ[9]    = {0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79};
const byte CMD_ZERO[9]    = {0xFF, 0x01, 0x87, 0x00, 0x00, 0x00, 0x00, 0x00, 0x78};
const byte CMD_ABC_OFF[9] = {0xFF, 0x01, 0x79, 0x00, 0x00, 0x00, 0x00, 0x00, 0x86};
const byte CMD_ABC_ON[9]  = {0xFF, 0x01, 0x79, 0xA0, 0x00, 0x00, 0x00, 0x00, 0xE6};

void setup() {
  Serial.begin(9600);
  co2SerialB.begin(9600);
  co2SerialC.begin(9600);
  while (!Serial) { ; }
  delay(500);
  printHelp();
}

void loop() {
  static unsigned long lastRead = 0;
  if (millis() - lastRead > 5000) {
    lastRead = millis();
    printReadings();
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toLowerCase();
    handleCommand(cmd);
  }
}

void handleCommand(const String& cmd) {
  if (cmd == "read") {
    printReadings();
  }
  else if (cmd == "zerob") {
    Serial.println(F(">> B: 送出歸零指令(設為 400 ppm)..."));
    sendCommand(co2SerialB, CMD_ZERO);
    Serial.println(F(">> 完成。約 1 分鐘後讀值會穩定"));
  }
  else if (cmd == "zeroc") {
    Serial.println(F(">> C: 送出歸零指令(設為 400 ppm)..."));
    sendCommand(co2SerialC, CMD_ZERO);
    Serial.println(F(">> 完成。約 1 分鐘後讀值會穩定"));
  }
  else if (cmd == "abcoff") {
    Serial.println(F(">> B + C: 關閉 ABC..."));
    sendCommand(co2SerialB, CMD_ABC_OFF);
    delay(100);
    sendCommand(co2SerialC, CMD_ABC_OFF);
    Serial.println(F(">> 完成。建議拔電重插以確保生效"));
  }
  else if (cmd == "abcon") {
    Serial.println(F(">> B + C: 打開 ABC..."));
    sendCommand(co2SerialB, CMD_ABC_ON);
    delay(100);
    sendCommand(co2SerialC, CMD_ABC_ON);
    Serial.println(F(">> 完成"));
  }
  else if (cmd == "help") {
    printHelp();
  }
  else if (cmd.length() > 0) {
    Serial.print(F(">> 未知指令: "));
    Serial.println(cmd);
  }
}

void sendCommand(SoftwareSerial& s, const byte* cmd) {
  s.listen();
  s.write(cmd, 9);
  delay(50);
}

int readCO2(SoftwareSerial& swSerial) {
  swSerial.listen();
  swSerial.write(CMD_READ, 9);

  byte response[9];
  unsigned long startTime = millis();
  while (swSerial.available() < 9 && (millis() - startTime) < 1000) {
    delay(10);
  }
  if (swSerial.available() < 9) return -1;
  swSerial.readBytes(response, 9);
  if (response[0] != 0xFF || response[1] != 0x86) return -2;

  byte crc = 0;
  for (int i = 1; i < 8; i++) crc += response[i];
  crc = 255 - crc + 1;
  if (response[8] != crc) return -3;

  return (response[2] << 8) + response[3];
}

void printReadings() {
  Serial.print(F("CO2_B = "));
  printCO2(readCO2(co2SerialB));
  Serial.print(F("    CO2_C = "));
  printCO2(readCO2(co2SerialC));
  Serial.println();
}

void printCO2(int v) {
  if (v < 0) {
    Serial.print(F("ERR("));
    Serial.print(v);
    Serial.print(F(")"));
  } else {
    Serial.print(v);
    Serial.print(F(" ppm"));
  }
}

void printHelp() {
  Serial.println();
  Serial.println(F("=== MH-Z19B/C 校準程式 ==="));
  Serial.println(F("指令: read | zerob | zeroc | abcoff | abcon | help"));
  Serial.println(F("流程: 戶外通風 >= 20 分鐘 -> abcoff -> zerob -> zeroc"));
  Serial.println();
}
