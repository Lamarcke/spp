import os

from inquirer.questions import json
from config.data_config import sqlite_conn
from exceptions.exceptions import HistoryError
from models.uploader_models import LibgenMetadata


class HistoryHandler:

    def __init__(self):
        self.db_conn = sqlite_conn()

    def stringfy_metadata(self, metadata: LibgenMetadata):
        return metadata.json(exclude={})
    
    def load_metadata(self, metadata_str: str):
        return json.loads(metadata_str)
    
    def check_duplicate(self, metadata: LibgenMetadata):
        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            possible_values = cursor.execute("SELECT * FROM spp WHERE metadata=%s", metadata_str)
            print(possible_values)
            return True

    def add_to_history(self, metadata: LibgenMetadata):
        if self.check_duplicate(metadata):
            raise HistoryError("Duplicated entry. Skipping.")
        
        with self.db_conn as conn:
            metadata_str = self.stringfy_metadata(metadata)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO spp (metadata, )")
            
            
            






