import logging
import os
from selenium.webdriver.remote.remote_connection import LOGGER

# Reduce the level of selenium's logger.
LOGGER.setLevel(logging.FATAL)


def logging_setup():
    logging_file = os.environ.get("LOG_FILE_PATH")
    if logging_file is None:
        logging_file = os.path.abspath(r".\logs.log")
    logging_file.encode(encoding="UTF-8")
    if not os.path.isfile(logging_file):
        c = open(logging_file, "w")

    _format = "%(asctime)s | %(levelname)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Allowing debug logs will also log selenium stuff in the file.
    logging.basicConfig(filename=logging_file, encoding="UTF-8", format=_format, level=logging.INFO, datefmt=date_fmt)
    print(f"Logging in file: ", logging_file)
