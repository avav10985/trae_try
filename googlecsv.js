function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  // 依照 Arduino 傳出的欄位：時間, 裝置ID, 溫度, pH, TDS, EC, 濁度, Lux, CO2_B, CO2_C
  var rowData = [
    new Date(),           // A: 自動生成時間
    data.device_id,       // B: 裝置名稱
    data.temp,            // C: 溫度
    data.ph,              // D: 酸鹼
    data.tds,             // E: 溶解 (TDS)
    data.ec,              // F: 導電 (EC)
    data.turb,            // G: 濁度
    data.lux,             // H: 光照
    data.c2b,             // I: CO2_B (改回 Arduino 原生 Key)
    data.c2c              // J: CO2_C (改回 Arduino 原生 Key)
  ];
  
  sheet.appendRow(rowData);
  return ContentService.createTextOutput("Success");
}