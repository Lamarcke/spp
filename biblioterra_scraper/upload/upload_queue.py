import json
import logging
import os.path
from typing import Iterable

from pydantic import ValidationError
import itertools

from biblioterra_scraper.exceptions import UploadQueueFileError
from biblioterra_scraper.exceptions.exceptions import UploadQueueError
from biblioterra_scraper.models.uploader_models import LibgenMetadata
from biblioterra_scraper.config import setup_upload_queue_log, setup_uploaded_files_log


class UploadQueue:
    """
    Manages the separate upload queue so that it's possible to download and upload books separately.
    UploadQueue should be responsible for saving metadata and filepaths to the upload queue file.
    It also should avoid duplicates from being added to queue and uploaded.
    """

    def __init__(self):
        self.metadata: LibgenMetadata | None = None
        self.queue_path = setup_upload_queue_log()
        self.uploaded_path = setup_uploaded_files_log()
        self.temp_queue_path = os.path.abspath(r".\temp_upload_queue.txt")

    @staticmethod
    def stringfy_metadata(metadata: LibgenMetadata) -> str:
        try:
            meta_str = metadata.json()
            return meta_str
        except Exception as e:
            logging.error(f"Error while stringfying {metadata}. Error: {e}", exc_info=True)
            raise UploadQueueError(e)

    @staticmethod
    def load_stringfied_metadata(metadata_str: str) -> LibgenMetadata:
        try:
            meta_dict = json.loads(metadata_str)
            meta_model = LibgenMetadata(**meta_dict)
            return meta_model
        except (ValidationError, Exception) as e:
            logging.error(f"Error while validating {metadata_str}. Error: {e}", exc_info=True)
            raise UploadQueueError(e)

    def _remove_temp_queue_file(self):
        if os.path.isfile(self.temp_queue_path):
            os.remove(self.temp_queue_path)
        else:
            logging.warning(f"{self.temp_queue_path} is not considered a valid file. "
                            f"Please check file permissions and method calls.")

            raise UploadQueueFileError(f"{self.temp_queue_path} is not considered a valid file. Aborting.")

    def _replace_queue_file(self):
        old_file = self.queue_path
        temp_file = self.temp_queue_path
        if os.path.isfile(old_file) and os.path.isfile(temp_file):
            # Renames temp_file name and path to the old_file's one.
            os.replace(temp_file, old_file)
        else:
            logging.warning(f"{old_file} or {temp_file} is not considered a valid file. "
                            f"Please check file permissions and method calls.")
            raise UploadQueueFileError(f"{old_file} or {temp_file} is not considered a valid file. Aborting.")

    def _queue_and_uploaded_generator(self) -> Iterable[tuple[str | None, str | None]]:
        """
        A generator that returns an iterator with lines from both the
        queue list file and from the uploaded log file.
        """
        queue_file = open(self.queue_path, "r")
        uploaded_file = open(self.queue_path, "r")

        # Thank you itertools for existing.
        for queue_line, uploaded_line in itertools.zip_longest(uploaded_file, queue_file, fillvalue=None):
            yield queue_line, uploaded_line

    def exists_on_queue_or_uploaded(self):
        """
        This method prevents that a file which has already been uploaded, or is already on upload queue is added
        again.
        """
        if self.metadata is None:
            raise UploadQueueError("Can't check for duplicates because no metadata was provided.")

        for queue_line, uploaded_line in self._queue_and_uploaded_generator():
            # Retrieves only the non-None values from the iterator.
            for valid_line in [line for line in [queue_line, uploaded_line] if line is not None]:
                # Checks if line is not empty
                if valid_line.strip():
                    try:
                        valid_line = valid_line.strip()
                        valid_line_model = self.load_stringfied_metadata(valid_line)
                        if valid_line_model == self.metadata:
                            return True
                    except (UploadQueueError, TypeError, ValueError, AttributeError):
                        pass

        return False

    def add_to_queue(self, metadata: LibgenMetadata):
        self.metadata = metadata
        if self.exists_on_queue_or_uploaded():
            logging.warning(f"{metadata} is in queue or has already been uploaded.")
            raise UploadQueueError("Duplicated entry. Skipping.")

        metadata_as_string = self.stringfy_metadata(metadata)
        try:
            with open(self.queue_path, "w") as f:
                f.write(metadata_as_string)
                logging.info(f"Added to queue: '{self.metadata.filepaths}' and it's metadata: '{self.metadata}'")
        except (BaseException, Exception) as e:
            logging.critical(f"Error while adding a file to queue.")
            logging.critical(f"Files: {self.metadata.filepaths}")
            logging.critical(f"File metadata: {self.metadata}")
            logging.critical(f"Error: {e}")
            raise UploadQueueFileError(e)

    def remove_from_queue(self, metadata: LibgenMetadata):
        """
        This method removes a file from upload queue.
        It should be called only after the given file has been uploaded or deemed invalid.
        Writes to a temporary file before commiting changes, and only commits if any changes where made.
        """

        self.metadata = metadata
        metadata_as_string = self.stringfy_metadata(metadata)

        removed_from_queue = False
        with open(self.temp_queue_path, "w") as temp:
            for line in open(self.queue_path, "r"):
                striped_line = line.strip()
                if striped_line:
                    if striped_line != metadata_as_string.strip():

                        # Do not write striped_line because the returns are removed.
                        # Causing the file to be written in a single line.
                        temp.write(line)

                    else:
                        removed_from_queue = True
        if removed_from_queue:
            try:
                self._replace_queue_file()
                logging.info(f"Removed from queue: '{self.metadata.filepaths}' and it's metadata: '{self.metadata}'")
            except (BaseException, Exception) as e:
                logging.critical(f"Failed to replace old queue file with new one. Error: {e}", exc_info=True)
                raise UploadQueueFileError(f"Failed to replace old queue file with new one, check folder permissions"
                                           f"for root and queue file folder. {e}")
        else:
            try:
                self._remove_temp_queue_file()

            except UploadQueueError as e:
                logging.info(f"Tried removing non-existing file from queue. {e}", exc_info=True)
                raise e

            except (BaseException, Exception) as e:
                logging.warning(f"Failed to remove temporary queue file. No changes made to original one. "
                                f"Error: {e}", exc_info=True)
                raise UploadQueueFileError(f"Failed to remove temporary queue file. No changes made to original one. "
                                           f"Error: {e}")
            logging.info(f"Tried removing non-existing file from queue. Metadata: {self.metadata}")
            raise UploadQueueError("Provided metadata does not match any file in queue.")
