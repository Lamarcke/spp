from scrapers_preservation.config import logging_setup, setup_driver
from scrapers_preservation.routines import elivros_downloader
from scrapers_preservation.upload import UploadQueue, LibgenUpload

if __name__ == '__main__':
    up_q = UploadQueue()
    lib_up = LibgenUpload()
    driver = setup_driver()
    logging_setup()
    for entry in up_q.get_current_queue():
        lib_up.make_upload(driver, entry)
        break



