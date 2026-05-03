"""感測器「無資料」代碼 — 統一給所有分析程式 import。

這 4 個常數不是使用者設定,所以不放在 config.py(gitignored),而是放在
這支 tracked 模組,Pi 端 git pull 就會自動拿到最新值。

寫入規則(由 rpi_gui_monitor.py 決定):
    -1 真實感測器斷線    → check_disconnect 會觸發警告
    -2 使用者 GUI 取消勾選 → 不警告
    -3 韌體沒送這個欄位   → 不警告
"""

DISCONNECT_CODE = -1
USER_DISABLED_CODE = -2
FIRMWARE_MISSING_CODE = -3
NO_DATA_CODES = {DISCONNECT_CODE, USER_DISABLED_CODE, FIRMWARE_MISSING_CODE}
