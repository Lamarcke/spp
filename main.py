from dotenv import load_dotenv

from config import logging_setup, setup_db
from config.data_config import setup_data_folder
from menu import SPPMenu


def spp_setup():
    load_dotenv()
    setup_data_folder()
    logging_setup()
    setup_db()


if __name__ == '__main__':
    spp_setup()
    spp = SPPMenu()
    spp.start()
