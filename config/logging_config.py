import logging
import os
from selenium.webdriver.remote.remote_connection import LOGGER

# Reduce the level of selenium's logger.
LOGGER.setLevel(logging.FATAL)

LOGGING_PATH = os.path.abspath("logs.log")


def validate_log_file():
    if not os.path.isfile(LOGGING_PATH):
        c = open(LOGGING_PATH, "w")


def logging_setup():
    validate_log_file()

    _format = "%(asctime)s | %(levelname)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Allowing debug logs will also log selenium stuff in the file.
    logging.basicConfig(filename=LOGGING_PATH, encoding="UTF-8", format=_format, level=logging.INFO, datefmt=date_fmt)
    print(f"Logging in file: ", LOGGING_PATH)
