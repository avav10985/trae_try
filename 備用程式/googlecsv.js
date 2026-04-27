function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);

  // 欄位順序：時間, 裝置ID, 溫度, pH, TDS, TDS(EC), EC, 濁度, Lux, CO2_B, CO2_C
  var rowData = [
    new Date(),           // A: 自動生成時間
    data.device_id,       // B: 裝置名稱
    data.temp,            // C: 溫度
    data.ph,              // D: 酸鹼
    data.tds,             // E: 溶解 (TDS, SEN0244)
    data.tdse,            // F: TDS(EC) - 由 EC 推算的 TDS,適用海水
    data.ec,              // G: 導電 (EC)
    data.turb,            // H: 濁度 (NTU)
    data.lux,             // I: 光照
    data.c2b,             // J: CO2_B
    data.c2c              // K: CO2_C
  ];

  sheet.appendRow(rowData);
  return ContentService.createTextOutput("Success");
}