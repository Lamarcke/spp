from scrapers_preservation.config import logging_setup
from scrapers_preservation.routines import elivros_downloader

if __name__ == '__main__':
    logging_setup()
    elivros_downloader()


