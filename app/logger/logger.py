import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger
import pytz
from app.config import settings


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        kwargs['json_ensure_ascii'] = False
        super(CustomJsonFormatter, self).__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        # Получаем уровень логирования и преобразуем его в верхний регистр, если он не равен None
        level = log_record.get("level", record.levelname)
        if level is not None:
            log_record["level"] = level.upper()
        else:
            log_record["level"] = "UNKNOWN"

        # Добавляем timestamp, если его нет
        if not log_record.get("timestamp"):
            yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
            now = datetime.now(yekaterinburg_tz)
            log_record["timestamp"] = now.strftime("%Y-%m-%d %H:%M:%S")

        # Вызываем метод суперкласса
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

# Определяем формат логирования
log_format = "%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s"
formatter = CustomJsonFormatter(log_format)

# Настраиваем обработчики и логгер
logHandler = logging.StreamHandler()
logHandler.setFormatter(formatter)

# Определяем путь к файлу лога
log_directory = os.path.dirname(__file__)
log_file_path = os.path.join(log_directory, 'app_logs.json')

# Проверяем существование директории и создаём, если необходимо
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Настраиваем обработчик для ротации логов
fileHandler = RotatingFileHandler(
    log_file_path, maxBytes=10 ** 6, backupCount=5, encoding='utf-8'
)
fileHandler.setFormatter(formatter)

logger = logging.getLogger()

# Предотвращаем многократное добавление обработчиков
if not logger.handlers:
    logger.addHandler(logHandler)
    logger.addHandler(fileHandler)

# Устанавливаем уровень логирования
logger.setLevel(settings.LOG_LEVEL)
