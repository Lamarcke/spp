import time

from config.driver_config import driver_setup
from exceptions.exceptions import UploaderFileError
from upload import LibgenUploadHandler


def libgen_uploader():
    uploader = LibgenUploadHandler()
    driver = driver_setup()

    while True:

        try:
            uploader.start_uploading(driver)

        except UploaderFileError as e:
            e_str = str(e)
            if e_str.find("No uploadable entries") != -1:
                time.sleep(180)
                driver = driver_setup()
                uploader = LibgenUploadHandler()
                continue
            
        

        except Exception as e:
            print(e)
            continue
