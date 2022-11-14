import filecmp
import json
import logging
import os.path
from typing import Iterable

from pydantic import ValidationError
import itertools
import shutil

from exceptions import HistoryFileError, HistoryError
from models.uploader_models import LibgenMetadata
from models.history_models import UploadHistoryEntry, DownloadHistoryEntry
from config import setup_upload_history, setup_download_folder, setup_download_history
from upload.helpers import UploadHelper


class HistoryHandler:
    """
    This class manages all file work related to building and managing download and upload histories.
    """

    def __init__(self):
        self.metadata: LibgenMetadata | None = None
        self.downloads_path = setup_download_folder()
        self.upload_history_path = setup_upload_history()
        self.temp_upload_history_path = os.path.abspath(r".\temp_upload_history.txt")
        self.download_history_path = setup_download_history()
        self.temp_download_history_path = os.path.abspath(r".\temp_download_history.txt")
        self.valid_extensions = ("epub", "pdf", "mobi")
        self.upload_helper = UploadHelper()

    def _get_download_dir(self):
        return os.listdir(self.downloads_path)

    @staticmethod
    def stringfy_download_history(download_entry: DownloadHistoryEntry) -> str:
        try:
            meta_str = download_entry.json()
            return meta_str
        except Exception as e:
            logging.error(f"Error while stringfying {download_entry}. Error: {e}", exc_info=True)
            raise HistoryError(e)

    @staticmethod
    def load_stringfied_download_history(download_str: str) -> DownloadHistoryEntry:
        """
        Use this for retrieving a download history file line as model.
        """
        try:
            download_str.strip()
            d_dict = json.loads(download_str)
            d_model = DownloadHistoryEntry(**d_dict)

            return d_model
        except (ValidationError, Exception) as e:
            logging.error(f"Error while validating {download_str}. Error: {e}", exc_info=True)
            raise HistoryError(e)

    @staticmethod
    def stringfy_uploaded_info(uploaded_info: UploadHistoryEntry) -> str:
        try:
            up_str = uploaded_info.json()
            return up_str
        except Exception as e:
            logging.error(f"Error while stringfying {uploaded_info}. Error: {e}", exc_info=True)
            raise HistoryError(e)

    @staticmethod
    def load_stringfied_uploaded_info(uploaded_info_str: str) -> UploadHistoryEntry:

        try:
            uploaded_info_str.strip()
            uploaded_dict = json.loads(uploaded_info_str)
            uploaded_model = UploadHistoryEntry(**uploaded_dict)
            return uploaded_model

        except (ValidationError, Exception) as e:
            logging.error(f"Error while validating {uploaded_info_str}. Error: {e}", exc_info=True)
            raise HistoryError(e)

    @staticmethod
    def _compare_plain_models(model1: LibgenMetadata, model2: LibgenMetadata) -> bool:
        """
        Compares basic info of models.
        This is mainly used to filter which values to check for duplicated files.

        """
        model1_plain = model1.copy(include={"title", "authors", "language", "source"})
        model2_plain = model2.copy(include={"title", "authors", "language", "source"})

        if model1_plain == model2_plain:
            return True
        else:
            return False

    @staticmethod
    def _remove_temp_file(temp_file_path: str):
        if os.path.isfile(temp_file_path):
            os.remove(temp_file_path)
        else:
            logging.warning(f"{temp_file_path} is not considered a valid file. "
                            f"Please check file permissions and method calls.")

            raise HistoryFileError(f"{temp_file_path} is not considered a valid file. Aborting.")

    @staticmethod
    def _replace_temp_file(temp_file_path: str, original_file_path: str):
        original_file_name = os.path.basename(original_file_path)
        if os.path.isfile(original_file_path) and os.path.isfile(temp_file_path):
            # Renames temp_file name and path to the old_file's one.
            try:
                original_file_backup_path = os.path.abspath(fr".\{original_file_name}.backup")
                # Makes a backup of the main file, just in case.
                shutil.copy(original_file_path, original_file_backup_path)
                shutil.move(temp_file_path, original_file_path)
            except (OSError, IOError) as e:
                logging.error("Error while replacing upload queue file.")
                logging.error(f"{e}", exc_info=True)
                raise HistoryFileError(f"Error while replacing upload queue file. {e}", )

        else:
            logging.warning(f"{original_file_path} or {temp_file_path} is not considered a valid file. "
                            f"Please check file permissions and method calls.")
            raise HistoryFileError(f"{original_file_path} or {temp_file_path} "
                                   f"is not considered a valid file. Aborting operation.")

    @staticmethod
    def metadata_as_folder_name(metadata: LibgenMetadata):
        """
        This helper method returns the metadata as a string ready to be used as folder name.
        """
        meta_str = f"{metadata.title}-{metadata.authors}-{metadata.language}-{metadata.source.name}"
        f_str_list = [char if char.isalnum() and not char.isspace() else "-" for char in meta_str]
        folder_name = "".join(f_str_list)
        return folder_name

    def move_to_main_download_folder(self, files: list[str], folder_name: str):
        successful_moves = []
        folder_path = os.path.join(self.downloads_path, folder_name)

        for temp_path in files:
            file_name = os.path.basename(temp_path)
            move_to = os.path.join(folder_path, file_name)
            if os.path.isfile(temp_path):

                if not os.path.isdir(folder_path):
                    os.mkdir(folder_path)

                shutil.move(temp_path, move_to)
                successful_moves.append(move_to)

        return successful_moves

    def get_download_history(self) -> Iterable[DownloadHistoryEntry]:
        """
        Subscribes to the current upload history and gets entries as validated upload infos.
        Mostly used for checking if a file has already been uploaded.

        Skips invalid entries.

        """
        for index, line in enumerate(open(self.download_history_path)):
            try:
                line_as_model = self.load_stringfied_download_history(line)
            except HistoryError as e:
                logging.warning("Found an invalid entry in download history history:")
                logging.error(f"{e}", exc_info=True)
                logging.warning(f"At download history file's line {index}")
                continue

            yield line_as_model

    def get_upload_history(self) -> Iterable[UploadHistoryEntry]:
        """
        Subscribes to the current upload queue and gets entries as validated metadatas.

        Skips invalid entries.

        """

        for index, line in enumerate(open(self.upload_history_path)):
            try:
                line_as_model = self.load_stringfied_download_history(line)
            except HistoryError as e:
                logging.warning("Found an invalid entry in upload history:")
                logging.error(f"{e}", exc_info=True)
                logging.warning(f"At line {index}")
                continue

            yield line_as_model

    def exists_on_download_history(self, metadata: LibgenMetadata):
        """
        This method checks if one or more files have already been downloaded.
        It searches download history for a match in metadata, and if it matches,
        and it's files are valid, return True.

        Generally, this should be run before making any downloads, to avoid resource waste.

        It works as a compromise between avoiding repeated downloads,
        but still downloading new files if current ones are not available.
        """

        for entry in self.get_download_history():
            if self._compare_plain_models(entry.metadata, metadata):
                # Metadata matches one in download history...
                valid_entry_paths = self.upload_helper.check_filepaths(entry.stored_at)
                if len(valid_entry_paths) > 0:
                    # And at least one of the stored paths is valid
                    return True

        return False

    def exists_in_upload_history(self, file_path: str) -> bool:
        """
        This method checks if a given file already exists in upload history.
        Evaluates to True if any entry matches the provided file path,
        or if a locally available file matches the one in file_path (shallow comparison).
        """

        if not os.path.isfile(file_path):
            logging.warning("Attempting to check upload history agaisnt invalid file")
            logging.warning(f"File: {file_path}")
            raise HistoryFileError(f"Provided file is not a valid file: {file_path}")

        for entry in self.get_upload_history():
            entry_file_path = entry.uploaded_file

            if os.path.isfile(entry_file_path) and filecmp.cmp(entry_file_path, file_path):
                return True

            if entry_file_path == file_path:
                return True

    def _append_to_history_file(self, temp_history_path: str, main_history_path: str, entry_str: str):
        """
        This method adds the entry_str to the main_story_path, using temp_history_path as a temp file.
        Also replaces the main file with the temp one after appending is done.
        """

        with open(temp_history_path, "w") as temp:
            for line in open(main_history_path, "r"):
                temp.write(line)
            temp.write(f"{entry_str}\n")

        self._replace_temp_file(temp_history_path, main_history_path)

    def add_to_download_history(self, entry: DownloadHistoryEntry):
        """
        This method adds a entry to the download history, and also moves its files to the main download folder.
        Also attaches valid metadata to the files' folder.

        Scrapers should use this after downloading files to make sure files are added in a proper manner.
        """

        valid_filepaths = self.upload_helper.check_filepaths(entry.stored_at)
        if len(valid_filepaths) == 0:
            raise HistoryFileError("Entry has no valid filepaths. "
                                   "This may be an file reading permission error..")

        move_to_folder_name = self.metadata_as_folder_name(entry.metadata)
        # Moves files to the main download folder.
        moved_files = self.move_to_main_download_folder(entry.stored_at, move_to_folder_name)

        if moved_files == 0:
            logging.error(f"Error while moving files: {entry.stored_at}")
            raise HistoryFileError(f"Error while moving files: {entry.stored_at}. "
                                   f"Check if path exists and permissions are correct")
        else:
            entry.stored_at = moved_files

        download_entry_str = self.stringfy_download_history(entry)

        try:
            self._append_to_history_file(self.temp_download_history_path, self.download_history_path, download_entry_str)
            logging.info(f"Added to download history: '{entry.stored_at}' and it's metadata: '{entry.metadata}'")

        except BaseException as e:
            logging.critical(f"Error while adding an entry to download history.")
            logging.critical(f"Files: {entry.stored_at}")
            logging.critical(f"File metadata: {entry.metadata}")
            logging.critical(f"Error: {e}")
            raise HistoryFileError(e)

    def add_to_upload_history(self, entry: UploadHistoryEntry):

        if self.exists_in_upload_history(entry.uploaded_file):
            logging.warning(f"Attempting to append duplicate file. {entry.uploaded_file}")
            logging.warning("File is already in upload history.")
            raise HistoryFileError(f"Attempting to append duplicate file. {entry.uploaded_file}")

        upload_entry_str = self.stringfy_uploaded_info(entry)

        try:
            self._append_to_history_file(self.temp_upload_history_path, self.upload_history_path, upload_entry_str)
            logging.info(f"Added to upload history: '{entry.uploaded_file}'")

        except BaseException as e:
            logging.critical(f"Error while adding an entry to upload history.")
            logging.critical(f"Entry file: {entry.uploaded_file}")
            logging.critical(f"Error: {e}", exc_info=True)
            raise HistoryFileError(e)
