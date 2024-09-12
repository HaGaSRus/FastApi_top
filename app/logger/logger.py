from pythonjsonlogger import jsonlogger
import logging
from datetime import datetime
import pytz
from app.config import settings
import os

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        kwargs['json_ensure_ascii'] = False
        super(CustomJsonFormatter, self).__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get("timestamp"):
            yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
            now = datetime.now(yekaterinburg_tz)
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
            log_record["timestamp"] = formatted_time
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname

# Настройте форматировщик для ведения журнала с помощью json_ensure_ascii=False
formatter = CustomJsonFormatter(
    "%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s"
)

# Настраиваем обработчики и логгер
logHandler = logging.StreamHandler()
logHandler.setFormatter(formatter)

# Определяем путь к файлу лога в той же директории, где находится основной скрипт
log_file_path = os.path.join(os.path.dirname(__file__), 'app_logs.json')

# Настраиваем обработчик для записи в файл
fileHandler = logging.FileHandler(log_file_path)
fileHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.addHandler(fileHandler)
logger.setLevel(settings.LOG_LEVEL)
