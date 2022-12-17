import os

from inquirer.questions import json
from exceptions.exceptions import HistoryError
from models.uploader_models import LibgenMetadata
from keys import sqlite_instance


class HistoryHandler:

    def __init__(self):
        self.db_conn = sqlite_instance

    def stringfy_metadata(self, metadata: LibgenMetadata):
        return metadata.json(exclude={})

    def load_metadata(self, metadata_str: str):
        return json.loads(metadata_str)

    def check_valid_file(self, file_path: str):
        return os.path.isfile(file_path)

    def check_duplicate(self, metadata: LibgenMetadata, file_path: str) -> bool:
        """
        Checks if a given file is a duplicate.
        Only marks as duplicate if the file on the database still exists.
        :param metadata:
        :param file_path:
        :return:
        """
        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            query = cursor.execute(
                "SELECT * FROM spp WHERE metadata=%s AND filepath=%s", (metadata_str, file_path))
            possible_values = query.fetchall()
            for value in possible_values:
                value_path = value["path"]
                if os.path.isfile(value_path):
                    return True
            return False

    def add_to_history(self, metadata: LibgenMetadata, file_path: str):
        if self.check_duplicate(metadata, file_path):
            raise HistoryError("Duplicated entry. Skipping.")

        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO spp (metadata, filepath) VALUES (%s, %s)", (metadata_str))

    def remove_from_history(self, entry_id: int, clean: bool = True):
        with self.db_conn as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM spp WHERE id=%d", (entry_id,))
