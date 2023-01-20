from dotenv import load_dotenv

from config import logging_setup
from menu import SPPMenu
import keys


def spp_setup():
    load_dotenv()
    logging_setup()


if __name__ == '__main__':
    spp_setup()
    spp = SPPMenu()
    spp.start()
