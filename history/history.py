import logging
import os
from typing import Generator

from inquirer.questions import json
from exceptions.exceptions import HistoryError
from models.uploader_models import LibgenMetadata
from keys import sqlite_instance


class HistoryHandler:

    def __init__(self):
        self.db_conn = sqlite_instance

    def stringfy_metadata(self, metadata: LibgenMetadata) -> str:
        return metadata.json()

    def load_metadata(self, metadata_str: str) -> dict:
        return json.loads(metadata_str)

    def check_valid_file(self, file_path: str):
        return os.path.isfile(file_path)

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
                print(value)
                value_path = value[1]
                if file_path is not None and value_path == file_path:
                    return True

                if value[2] != 0:
                    return True

            return False

    def get_all_history(self) -> Generator[LibgenMetadata, None, None]:
        with self.db_conn as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM spp")
            results = cursor.fetchall()

        for result in results:
            metadata_str = result["metadata"]
            metadata = self.load_metadata(metadata_str)
            metadata_as_model = LibgenMetadata(**metadata)
            yield metadata_as_model

    def _validate_file_path(self, file_path: str):
        if not os.path.isabs(file_path):
            raise HistoryError("File path must be absolute.")

    def add_to_history(self, metadata: LibgenMetadata, file_path: str):
        if self.check_duplicate(metadata, file_path):
            raise HistoryError("Duplicated entry. Skipping.")

        self._validate_file_path(file_path)

        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO spp (metadata, filepath) VALUES (?, ?)", (metadata_str, file_path))

        logging.info(f"Added {file_path} to history.")

    def remove_from_history(self, entry_id: int, clean: bool = True):
        with self.db_conn as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT metadata, filepath FROM spp WHERE id=%d", (entry_id,))
