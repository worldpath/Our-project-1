import logging
import json
import sys
from logging.handlers import RotatingFileHandler

def build_logger(name: str, path: str = 'bot.log', level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            payload = {
                'ts': self.formatTime(record, datefmt='%Y-%m-%dT%H:%M:%SZ'),
                'level': record.levelname,
                'name': record.name,
                'msg': record.getMessage(),
            }
            if record.exc_info:
                payload['exc_info'] = self.formatException(record.exc_info)
            return json.dumps(payload)
    
    fh = RotatingFileHandler(path, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(JsonFormatter())
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(JsonFormatter())
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger