import logging
import os

class BotLogger:
    def __init__(self, log_file='log_bot.log', log_dir='logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(os.path.dirname(__file__), log_dir, log_file)
        self.logger = logging.getLogger('logger_bot')
        self.logger.setLevel(logging.DEBUG)

        if not self.logger.handlers:
            file_handler = logging.FileHandler(self.log_path, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            formatter = logging.Formatter(
               '[%(asctime)s] %(levelname)s in %(filename)s:%(lineno)d %(funcName)s() - %(message)s'
            )
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

obj_log = BotLogger()
logger = obj_log.get_logger()