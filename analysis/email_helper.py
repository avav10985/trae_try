"""
Email 寄送共用模組(library,不是可執行程式所以沒有 _email 後綴)。
任何 *_email.py 檔案都從這裡 import send_email()。
"""
import smtplib
from email.mime.text import MIMEText

from config import (
    EMAIL_ENABLED, EMAIL_SENDER, EMAIL_APP_PASSWORD,
    EMAIL_RECEIVER, EMAIL_SUBJECT_PREFIX,
)


def is_configured():
    """判斷 email 設定是否齊全"""
    if not EMAIL_ENABLED:
        return False
    if (not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECEIVER
            or "your_account" in EMAIL_SENDER or "xxxx" in EMAIL_APP_PASSWORD):
        return False
    return True


def send_email(subject, body):
    """
    寄送一封 email。Gmail SMTP / SSL 465。
    回傳 (success: bool, error_msg: str | None)
    """
    if not EMAIL_ENABLED:
        return False, "EMAIL_ENABLED = False"
    if not is_configured():
        return False, "Email 設定未完成,請填好 config.py 的 EMAIL_* 欄位"

    try:
        msg = MIMEText(body, _charset='utf-8')
        msg['Subject'] = f"{EMAIL_SUBJECT_PREFIX} {subject}"
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD.replace(" ", ""))
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)
