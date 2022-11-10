import json
import logging
import os.path
from typing import Iterable

from pydantic import ValidationError
import itertools

from scrapers_preservation.exceptions import UploadQueueFileError
from scrapers_preservation.exceptions.exceptions import UploadQueueError
from scrapers_preservation.models.uploader_models import LibgenMetadata, UploadedFileInfo
from scrapers_preservation.config import setup_upload_queue, setup_upload_history


class UploadQueue:
    """
    Manages the separate upload queue so that it's possible to download and upload books separately.
    UploadQueue should be responsible for saving metadata and filepaths to the upload queue file.
    It also should avoid duplicates from being added to queue and uploaded.
    """

    def __init__(self):
        self.metadata: LibgenMetadata | None = None
        self.queue_path = setup_upload_queue()
        self.history_path = setup_upload_history()
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
        """
        Use this for retrieving metadata_str as a LibgenMetadata object.
        """
        try:
            metadata_str.strip()
            meta_dict = json.loads(metadata_str)
            meta_model = LibgenMetadata(**meta_dict)

            return meta_model
        except (ValidationError, Exception) as e:
            logging.error(f"Error while validating {metadata_str}. Error: {e}", exc_info=True)
            raise UploadQueueError(e)

    @staticmethod
    def stringfy_uploaded_info(uploaded_info: UploadedFileInfo) -> str:
        try:
            up_str = uploaded_info.json()
            return up_str
        except Exception as e:
            logging.error(f"Error while stringfying {uploaded_info}. Error: {e}", exc_info=True)
            raise UploadQueueError(e)

    @staticmethod
    def load_stringfied_uploaded_info(uploaded_info_str: str) -> UploadedFileInfo:
        try:
            uploaded_info_str.strip()
            uploaded_dict = json.loads(uploaded_info_str)
            uploaded_model = UploadedFileInfo(**uploaded_dict)
            return uploaded_model

        except (ValidationError, Exception) as e:
            logging.error(f"Error while validating {uploaded_info_str}. Error: {e}", exc_info=True)
            raise UploadQueueError(e)

    @staticmethod
    def _compare_plain_models(model1: LibgenMetadata, model2: LibgenMetadata) -> bool:
        """
        Compares models while excluding filepaths.
        """
        model1_plain = model1.copy(exclude={"filepaths"})
        model2_plain = model2.copy(exclude={"filepaths"})

        if model1_plain == model2_plain:
            return True
        else:
            return False

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

    def _queue_and_uploaded_generator(self) -> Iterable[tuple[LibgenMetadata | None, UploadedFileInfo | None]]:
        """
        Uses the get method of both queue and uploaded files to build a generator with validated entries.

        """
        queue_gen = self.get_current_queue()
        history_gen = self.get_current_history()

        # Thank you itertools for existing.
        # Make sure queue_file comes as the first paramater.
        for queue_line, uploaded_line in itertools.zip_longest(queue_gen, history_gen, fillvalue=None):
            yield queue_line, uploaded_line

    def exists_on_queue_or_history(self):
        """
        This method prevents that a file which has already been uploaded, or is already on upload queue is added
        again.
        """

        if self.metadata is None:
            raise UploadQueueError("Can't check for duplicates because no metadata was provided.")

        for queue_line, uploaded_line in self._queue_and_uploaded_generator():

            if uploaded_line is not None:
                try:
                    if uploaded_line.metadata == self.metadata:
                        # List comp
                        unique_filepaths = [filepath for filepath in self.metadata
                                            if filepath not in uploaded_line.metadata.filepaths]
                        if len(unique_filepaths) > 0:
                            self.metadata.filepaths = unique_filepaths
                        else:
                            return True

                except:
                    pass

            if queue_line is not None:
                # Checks if line is not empty

                try:
                    if self._compare_plain_models(queue_line, self.metadata):
                        unique_filepaths = [filepath for filepath in self.metadata.filepaths
                                            if filepath not in queue_line.filepaths]

                        if len(unique_filepaths) > 0:
                            self.metadata.filepaths = unique_filepaths

                        else:
                            return True
                except:
                    continue

        return False

    def get_current_history(self) -> Iterable[UploadedFileInfo]:
        """
        Subscribes to the current upload history and gets entries as validated upload infos.
        Mostly used for checking if a file has already been uploaded.

        Skips invalid entries.

        """
        for line in open(self.history_path):
            line_as_model = self.load_stringfied_uploaded_info(line)
            yield line_as_model

    def get_current_queue(self) -> Iterable[LibgenMetadata]:
        """
        Subscribes to the current upload queue and gets entries as validated metadatas.

        Skips invalid entries.

        """
        for line in open(self.queue_path):
            try:
                line_as_model = self.load_stringfied_metadata(line)
            except UploadQueueError:
                continue
            yield line_as_model

    def add_to_queue(self, metadata: LibgenMetadata):
        self.metadata = metadata

        if self.exists_on_queue_or_history():
            logging.warning(f"{metadata} is in queue or has already been uploaded.")
            raise UploadQueueError("Duplicated entry. Skipping.")

        metadata_as_string = self.stringfy_metadata(metadata)

        try:
            with open(self.temp_queue_path, "w") as temp:
                for line in open(self.queue_path, "r"):
                    temp.write(line)
                temp.write(f"{metadata_as_string}\n")

            self._replace_queue_file()
            logging.info(f"Added to queue: '{self.metadata.filepaths}' and it's metadata: '{self.metadata}'")

        except (BaseException, Exception) as e:
            logging.critical(f"Error while adding a file to queue.")
            logging.critical(f"Files: {self.metadata.filepaths}")
            logging.critical(f"File metadata: {self.metadata}")
            logging.critical(f"Error: {e}")
            raise UploadQueueFileError(e)

    def remove_from_queue(self, metadata: LibgenMetadata):
        """
        This method removes a exact match from upload queue.

        It's recommended to only attempt to remove values originated from subscribe_to_queue().

        It should also be called after the given file has been uploaded or deemed invalid.
        Writes to a temporary file before commiting changes, and only commits if any changes where made.
        """

        self.metadata = metadata

        removed_from_queue = False

        with open(self.temp_queue_path, "w") as temp:
            for line in open(self.queue_path, "r"):
                striped_line = line.strip()
                if striped_line:

                    # We use this opportunity to validate each line and avoid writing the invalid ones.
                    try:
                        line_as_model = self.load_stringfied_metadata(striped_line)
                    except:
                        continue

                    if line_as_model != self.metadata:
                        # Do not write striped_line because the returns are removed.
                        # Causing the file to be written in a single line.

                        temp.write(line)

                    else:
                        removed_from_queue = True

            temp.close()

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
