function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  // 按照水平模式排列欄位：時間, 裝置ID, 溫度, pH, TDS, EC, 濁度, Lux, CO2_B, CO2_C
  var rowData = [
    new Date(),           // A: 自動生成時間
    data.device_id,       // B: 裝置名稱
    data.temp,            // C: 溫度
    data.ph,              // D: 酸鹼
    data.tds,             // E: 溶解 (TDS)
    data.ec,              // F: 導電 (EC)
    data.turb,            // G: 濁度
    data.lux,             // H: 光照
    data.co2b,            // I: CO2_B
    data.co2c             // J: CO2_C
  ];
  
  sheet.appendRow(rowData);
  return ContentService.createTextOutput("Success");
}