from pydantic import BaseModel, Field
import os

DEFAULT_DOWNLOAD_PATH = os.path.join("data", "downloads")
DEFAULT_TEMP_DOWNLOAD_PATH = os.path.join("data", "temp_downloads")
DEFAULT_HISTORY_DB_PATH = os.path.join("data", "history.db")


class SPPSettingsModel(BaseModel):
    max_downloads: int = Field(default=100)
    downloads_path: str = Field(default=os.path.abspath(DEFAULT_DOWNLOAD_PATH))
    temp_downloads_path: str = Field(default=os.path.abspath(DEFAULT_TEMP_DOWNLOAD_PATH))
    history_db_path: str = Field(default=os.path.abspath(DEFAULT_HISTORY_DB_PATH))
