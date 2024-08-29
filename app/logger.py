from pythonjsonlogger import jsonlogger
import logging
from datetime import datetime
import pytz
from app.config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get("timestamp"):
            # Get the current time in UTC and convert it to Yekaterinburg time zone
            yekaterinburg_tz = pytz.timezone('Asia/Yekaterinburg')
            now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(yekaterinburg_tz)
            formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")  # Desired time format
            log_record["timestamp"] = formatted_time
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname

# Set up the formatter for logging
formatter = CustomJsonFormatter(
    "%(timestamp)s %(level)s %(message)s %(module)s %(funcName)s"
)

# Set up the handler and logger
logHandler = logging.StreamHandler()
logHandler.setFormatter(formatter)

logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(settings.LOG_LEVEL)