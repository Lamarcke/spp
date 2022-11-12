from scrapers_preservation.config import setup_driver
from scrapers_preservation.upload import LibgenUpload, UploadQueue


def upload_from_queue(num_of_uploads: int = 0):
    """
    This function is a pre-made script that automatically uploads books in the upload queue.

    This is the recommended way to upload files.
    """

    lib_up = LibgenUpload()
    queue = UploadQueue()
    driver = setup_driver()

    for index, entry in enumerate(queue.get_current_queue()):
        if 0 < num_of_uploads < index:
            break

        lib_up.make_upload(driver, entry)







