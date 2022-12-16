from config import logging_setup, db_setup
from config.data_config import setup_data_folder
from menu import SPPMenu
from dotenv import load_dotenv

if __name__ == '__main__':
    setup_data_folder()
    load_dotenv()
    logging_setup()
    db_setup()
    spp = SPPMenu()
