import logging
import os
from typing import Generator

from inquirer.questions import json
from exceptions.exceptions import HistoryError
from models.history_models import HistoryEntry
from models.uploader_models import LibgenMetadata
from keys import sqlite_instance


class HistoryHandler:

    def __init__(self):
        self.db_conn = sqlite_instance
        self.valid_extensions = ("epub", "pdf", "mobi")

    def _remove_file(self, file_path: str):
        try:
            os.remove(file_path)
        except (OSError, FileNotFoundError):
            logging.error(f"Could not remove file {file_path}")

    def _is_path_valid(self, file_path: str):
        file_path.encode("UTF-8")
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return True

        return False

    def _is_extension_valid(self, file_path: str):
        if file_path.endswith(self.valid_extensions):
            return True

        return False

    def stringfy_metadata(self, metadata: LibgenMetadata) -> str:
        return metadata.json()

    def load_metadata(self, metadata_str: str) -> dict:
        return json.loads(metadata_str)

    def check_duplicate(self, metadata: LibgenMetadata, file_path: str | None = None) -> bool:
        """
        Checks if a given file is a duplicate.
        :param metadata: metadata of the file
        :param file_path: absolute filepath to file. may be omitted if the file is not yet downloaded.
        :return: true if file is duplicate and still exists or as already been uploaded
        """
        if file_path:
            self._validate_file_path(file_path)

        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            query = cursor.execute(
                "SELECT metadata, filepath, uploaded FROM spp WHERE metadata=?", (metadata_str,))
            possible_values: list[tuple] = query.fetchall()
            for value in possible_values:
                value_path = value[1]
                value_uploaded = value[2]

                if value_uploaded != 0:
                    return True

                if file_path is not None:
                    if value_path == file_path:
                        return True
                else:
                    return True

            return False

    def get_all_history(self) -> Generator[LibgenMetadata, None, None]:
        with self.db_conn as conn:
            cursor = conn.cursor()
            for row in cursor.execute("SELECT id, metadata, filepath, uploaded, uploaded_at "
                                      "FROM spp"):
                metadata_str = row[1]
                metadata = self.load_metadata(metadata_str)
                metadata_as_model = LibgenMetadata(**metadata)
                yield metadata_as_model

    def get_num_uploadable_entries(self) -> int:
        with self.db_conn as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM spp WHERE uploaded=0")
            count = cursor.fetchone()
            return count[0]

    def get_uploadable_history(self) -> Generator[HistoryEntry, None, None]:
        with self.db_conn as conn:
            cursor = conn.cursor()
            count = self.get_num_uploadable_entries()
            if count == 0:
                logging.info("No files to upload.")
                raise FileNotFoundError("No files to upload.")

            for row in cursor.execute("SELECT id, metadata, filepath, uploaded, uploaded_at "
                                      "FROM spp WHERE uploaded=0"):
                entry_id = row[0]
                metadata_str = row[1]
                file_path = row[2]
                metadata = self.load_metadata(metadata_str)
                metadata_as_model = LibgenMetadata(**metadata)
                if not self._is_path_valid(file_path):
                    logging.warning(f"File {file_path} does not exist. Skipping.")
                    continue
                elif not self._is_extension_valid(file_path):
                    logging.warning(f"File {file_path} does not exist. Skipping.")
                    continue

                history_entry = HistoryEntry(entry_id=entry_id, file_path=file_path, metadata=metadata_as_model)

                yield history_entry

    def _validate_file_path(self, file_path: str):
        if not os.path.isabs(file_path):
            raise HistoryError("File path must be absolute.")
        # Make sure to use inverse (!) boolean logic here.
        if not self._is_path_valid(file_path) or not self._is_extension_valid(file_path):
            raise HistoryError("File path or extension is invalid.")

    def add_to_history(self, metadata: LibgenMetadata, file_path: str):
        if self.check_duplicate(metadata, file_path):
            raise HistoryError("Duplicated entry. Skipping.")

        self._validate_file_path(file_path)

        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO spp (metadata, filepath, uploaded) VALUES (?, ?, ?)", (metadata_str, file_path, 0))

            last_id = cursor.lastrowid
            cursor.execute("SELECT id, metadata, filepath FROM spp WHERE id=?", (last_id,))
            added_entry = cursor.fetchone()
            if added_entry is None or added_entry[1] != metadata_str or added_entry[2] != file_path:
                logging.error(f"Could not add entry to history.")
                raise HistoryError("Could not add entry to history.")

        logging.info(f"Added {file_path} to history.")

    def mark_as_uploaded(self, entry_id: int, uploaded_at: str | None = None):
        with self.db_conn as conn:
            cursor = conn.cursor()
            if uploaded_at:
                cursor.execute("UPDATE spp SET uploaded=1, uploaded_at=? WHERE id=?",
                               (uploaded_at, entry_id))
            else:
                cursor.execute("UPDATE spp SET uploaded=1 WHERE id=?", (entry_id,))
            logging.info(f"Marked entry {entry_id} as uploaded.")

    def remove_from_history(self, entry_id: int, clean: bool = True):
        with self.db_conn as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata, filepath FROM spp WHERE id=%d", (entry_id,))
            (metadata_str, file_path) = cursor.fetchone()
            metadata = self.load_metadata(metadata_str)
            metadata_as_model = LibgenMetadata(**metadata)
            if clean:
                self._remove_file(file_path)
            cursor.execute("DELETE FROM spp WHERE id=?", (entry_id,))
            logging.info(f"Removed {entry_id} from history.")
