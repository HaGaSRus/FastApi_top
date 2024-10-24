from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import logging
from pythonjsonlogger import jsonlogger
from datetime import datetime
import pytz
import os

from app.config import settings


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


formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s")

log_file_path = os.path.join(os.path.dirname(__file__), 'app_logs.json')
fileHandler = RotatingFileHandler(log_file_path, maxBytes=5 * 1024 * 1024, backupCount=5)
fileHandler.setFormatter(formatter)

streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(fileHandler)
logger.addHandler(streamHandler)
logger.setLevel(settings.LOG_LEVEL)

