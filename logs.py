import logging
import os

class Log:
    def __init__(self, logger_name, log_file):
        # Create a custom logger
        self.logger = logging.getLogger(logger_name)

        # Set level of logger
        self.logger.setLevel(logging.DEBUG)

        # Specify the directory where the log files will be saved
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create file handler
        log_file_path = os.path.join(log_dir, log_file)
        f_handler = logging.FileHandler(log_file_path)
        f_handler.setLevel(logging.DEBUG)

        # Create formatter and add it to handler
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        f_handler.setFormatter(f_format)

        # Add handler to the logger
        self.logger.addHandler(f_handler)

    def get_logger(self):
        return self.logger