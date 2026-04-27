/*
 * SEN0169 軟體兩點校準程式
 *
 * 用途：
 *   不依賴硬體 gain 電位器，直接用 pH 7 與 pH 4 兩個緩衝液量到的電壓
 *   計算 slope 與 offset，套用到主程式即可。
 *
 * 接線：
 *   pH 板 BNC -> pH 電極
 *   pH 板訊號 -> Arduino A2  (與主程式一致)
 *   VCC 5V, GND
 *
 * 使用步驟（序列埠監視器，鮑率 9600，行尾選 "Newline"）：
 *   1. 燒錄此程式 -> 開啟序列埠監視器
 *   2. 電極泡 pH 7.00 緩衝液 -> 等讀值穩定（電壓變化 < 0.005 V 持續 30 秒）
 *   3. 輸入  cal7   -> 記錄當前電壓為 V7
 *   4. 洗電極 -> 泡 pH 4.00 緩衝液 -> 等讀值穩定
 *   5. 輸入  cal4   -> 記錄當前電壓為 V4
 *   6. 輸入  calc   -> 印出 slope 與 offset
 *   7. 把印出的兩個數字抄到主程式 uno_sensor_serial_with_temp_comp.ino
 *
 * 其他指令：
 *   reset -> 清除已記錄的 V7、V4
 *   help  -> 列出指令
 */

#define PH_PIN          A2
#define SAMPLE_COUNT    40    // 一次平均取樣數
#define PRINT_INTERVAL  1000  // 螢幕更新間隔 (ms)

float v7 = NAN;
float v4 = NAN;

void setup() {
  pinMode(PH_PIN, INPUT);
  Serial.begin(9600);
  while (!Serial) { ; }
  delay(200);
  printHelp();
}

void loop() {
  static unsigned long lastPrint = 0;

  if (millis() - lastPrint > PRINT_INTERVAL) {
    lastPrint = millis();
    float v = readVoltageAvg();
    Serial.print("V = ");
    Serial.print(v, 4);
    Serial.print(" V    [V7=");
    printSlot(v7);
    Serial.print("  V4=");
    printSlot(v4);
    Serial.println("]");
  }

  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    cmd.toLowerCase();
    handleCommand(cmd);
  }
}

void handleCommand(const String& cmd) {
  if (cmd == "cal7") {
    v7 = readVoltageAvg();
    Serial.print(">> 已記錄 V7 = ");
    Serial.print(v7, 4);
    Serial.println(" V  (pH 7.00)");
  }
  else if (cmd == "cal4") {
    v4 = readVoltageAvg();
    Serial.print(">> 已記錄 V4 = ");
    Serial.print(v4, 4);
    Serial.println(" V  (pH 4.00)");
  }
  else if (cmd == "calc") {
    computeAndPrint();
  }
  else if (cmd == "reset") {
    v7 = NAN;
    v4 = NAN;
    Serial.println(">> V7、V4 已清除");
  }
  else if (cmd == "help") {
    printHelp();
  }
  else if (cmd.length() > 0) {
    Serial.print(">> 未知指令: ");
    Serial.println(cmd);
  }
}

void computeAndPrint() {
  if (isnan(v7) || isnan(v4)) {
    Serial.println(">> 錯誤：必須先完成 cal7 與 cal4");
    return;
  }
  if (fabs(v7 - v4) < 0.05) {
    Serial.println(">> 錯誤：V7 與 V4 太接近，請確認電極或緩衝液");
    return;
  }

  float slope  = (7.00f - 4.00f) / (v7 - v4);
  float offset = 7.00f - slope * v7;

  Serial.println();
  Serial.println("====== 校準結果 ======");
  Serial.print("V7 (pH 7.00) = ");  Serial.print(v7, 4);     Serial.println(" V");
  Serial.print("V4 (pH 4.00) = ");  Serial.print(v4, 4);     Serial.println(" V");
  Serial.print("slope        = ");  Serial.println(slope, 4);
  Serial.print("offset       = ");  Serial.println(offset, 4);
  Serial.println();
  Serial.println("複製到主程式 (uno_sensor_serial_with_temp_comp.ino):");
  Serial.print("  float phRaw = ");
  Serial.print(slope, 4);
  Serial.print(" * phVoltage + (");
  Serial.print(offset, 4);
  Serial.println(");");
  Serial.println("======================");
  Serial.println();
}

void printSlot(float v) {
  if (isnan(v)) Serial.print("--");
  else          Serial.print(v, 4);
}

void printHelp() {
  Serial.println();
  Serial.println("=== SEN0169 軟體兩點校準 ===");
  Serial.println("指令： cal7 | cal4 | calc | reset | help");
  Serial.println("流程：泡 pH7 等穩定 -> cal7 -> 洗淨 -> 泡 pH4 等穩定 -> cal4 -> calc");
  Serial.println();
}

float readVoltageAvg() {
  int buf[SAMPLE_COUNT];
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    buf[i] = analogRead(PH_PIN);
    delay(10);
  }
  int minV = buf[0], maxV = buf[0];
  long sum = 0;
  for (int i = 0; i < SAMPLE_COUNT; i++) {
    if (buf[i] < minV) minV = buf[i];
    if (buf[i] > maxV) maxV = buf[i];
    sum += buf[i];
  }
  sum -= minV;
  sum -= maxV;
  float avgADC = (float)sum / (SAMPLE_COUNT - 2);
  return avgADC * (5.0f / 1023.0f);
}
