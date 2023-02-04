from sqlite3 import OperationalError
import time

from config.driver_config import driver_setup
from exceptions.exceptions import UploaderFileError
from history.history import HistoryHandler
from upload import LibgenUploadHandler

from selenium.common import WebDriverException


def libgen_uploader():
    uploader = LibgenUploadHandler()
    history = HistoryHandler()
    driver = driver_setup()

    uploadable_count = history.get_num_uploadable_entries()

    if uploadable_count == 0:
        print("No uploadable entries.")
        return
    else:
        print(f"Found {uploadable_count} entries ready for upload.")

    while True:

        try:
            uploader.start_uploading(driver)

        except UploaderFileError as e:
            e_str = str(e)
            if e_str.find("No uploadable entries") != -1:
                break

        except WebDriverException as e:
            driver = driver_setup()
            uploader = LibgenUploadHandler()
            continue

        except Exception as e:
            print(e)
            continue
