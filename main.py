from config import logging_setup
from menu import SPPMenu
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    logging_setup()
    spp = SPPMenu()
    spp.start()
