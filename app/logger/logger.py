import html
from logging.handlers import RotatingFileHandler
import logging
import requests
from pythonjsonlogger import jsonlogger
from datetime import datetime
import pytz
import os
from app.config import settings

TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
CHAT_ID = settings.CHAT_ID


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        kwargs['json_ensure_ascii'] = False
        super().__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        if not log_record.get("timestamp"):
            tz = pytz.timezone('Asia/Yekaterinburg')
            log_record["timestamp"] = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

        level = log_record.get("level") or record.levelname
        log_record["level"] = level.upper() if level else "NOTSET"


class TelegramHandler(logging.Handler):
    """Кастомный логгер для отправки сообщений в Telegram"""
    def __init__(self, token, chat_id, level=logging.ERROR):
        super().__init__(level)
        self.token = token
        self.chat_id = chat_id

    def emit(self, record):
        log_entry = self.format(record)
        log_entry = html.escape(log_entry)
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": log_entry, "parse_mode": "HTML"}
            response = requests.post(url, json=payload)

            response.raise_for_status()
        except Exception as e:
            print(f"Ошибка при отправке сообщения в Telegram: {e}")


telegram_handler = TelegramHandler(
    token=settings.TELEGRAM_TOKEN,
    chat_id=settings.CHAT_ID,
)


formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s")
telegram_handler.setFormatter(formatter)


log_file_path = os.path.join(os.path.dirname(__file__), 'app_logs.json')
fileHandler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5)
fileHandler.setFormatter(formatter)

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(fileHandler)
logger.addHandler(streamHandler)
logger.addHandler(telegram_handler)
logger.setLevel(settings.LOG_LEVEL)
