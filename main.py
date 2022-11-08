from biblioterra_scraper.config import logging_setup
from biblioterra_scraper.routines import elivros_downloader

if __name__ == '__main__':
    logging_setup()
    elivros_downloader()


