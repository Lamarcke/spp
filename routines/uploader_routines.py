from config import setup_driver
from upload import LibgenUpload, HistoryHandler


def upload_from_queue(human_confirmation=False, num_of_uploads: int = 0):
    """
    This function is a pre-made script that automatically uploads books in the upload queue.

    This is the recommended way to upload files.
    """

    lib_up = LibgenUpload(human_confirmation=human_confirmation)
    queue = HistoryHandler()
    driver = setup_driver()

    for index, entry in enumerate(queue.get_upload_history()):
        if 0 < num_of_uploads < index:
            break

        lib_up.make_upload(driver, entry)
