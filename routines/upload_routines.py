import time

from config.driver_config import driver_setup
from upload import LibgenUploadHandler


def libgen_uploader():
    uploader = LibgenUploadHandler()
    driver = driver_setup()

    while True:

        try:
            uploader.start_uploading(driver)

        except Exception as e:
            print(e)
            uploader = LibgenUploadHandler()
            driver = driver_setup()
