import logging
from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def __init__(self, *args, **kwargs):
        # Инициализация форматера с ключами JSON
        super().__init__(*args, **kwargs)

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = self.formatTime(record, self.datefmt)  # Устанавливаем временную метку
        if not log_record.get('level'):
            log_record['level'] = record.levelname  # Устанавливаем уровень логирования

# Конфигурация логгера
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Настройка JSON форматтера
json_formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(module)s %(funcName)s %(message)s')

# Создание и настройка обработчика
console_handler = logging.StreamHandler()
console_handler.setFormatter(json_formatter)

# Добавляем обработчик к логгеру
logger.addHandler(console_handler)

# Пример логирования
logger.info("This is an info log")
logger.error("This is an error log")
