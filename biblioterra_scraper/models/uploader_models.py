from enum import Enum

from pydantic import BaseModel, Field
from selenium.webdriver.remote.webelement import WebElement


class AvailableSources(str, Enum):
    elivros = "elivros.love"


class ValidTopics(str, Enum):
    fiction = "fiction"
    scitech = "sci-tech"


class LibgenMetadata(BaseModel):
    topic: ValidTopics
    title: str
    authors: str
    language: str
    series: str | None = Field(None)
    description: str | None = Field(None)
    pages: str | None = Field(None)
    filepaths: list[str] = Field(..., min_length=1)
    source: AvailableSources  # Source for metadata and uploading.


class UploadedFileInfo(BaseModel):
    metadata: LibgenMetadata
    available_at: str  # URL at which the file is available for moderation.


class UploadMetadataElements(BaseModel):
    title: WebElement
    authors: WebElement
    series: WebElement
    description: WebElement
    pages: WebElement
    language: WebElement

    class Config:
        arbitrary_types_allowed = True

