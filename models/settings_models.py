from pydantic import BaseModel, Field
import os

DEFAULT_DOWNLOAD_PATH = os.path.sep.join(("data", "downloads"))
DEFAULT_TEMP_DOWNLOAD_PATH = os.path.sep.join(("data", "temp_downloads"))


class SPPSettingsModel(BaseModel):
    max_downloads: int = Field(default=100)
    downloads_path: str = Field(default=DEFAULT_DOWNLOAD_PATH)
    temp_downloads_path: str = Field(default=DEFAULT_TEMP_DOWNLOAD_PATH)
