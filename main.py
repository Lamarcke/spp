from scrapers_preservation.config import logging_setup, setup_driver
from scrapers_preservation.routines import elivros_downloader
from scrapers_preservation.upload import UploadQueue, LibgenUpload

if __name__ == '__main__':
    logging_setup()
    elivros_downloader()



