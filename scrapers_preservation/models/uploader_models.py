from enum import Enum

from pydantic import BaseModel, Field
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select


class AvailableSources(str, Enum):
    elivros = "elivros.love"


class ValidLanguages(str, Enum):
    # Values should be the same as in libgen.bz language select input.
    english = "English"
    portuguese = "Portuguese"


class ValidTopics(str, Enum):
    fiction = "fiction"
    scitech = "sci-tech"


class LibgenMetadata(BaseModel):
    # Adding or removing anything will break existing update queue and upload history entries.
    topic: ValidTopics
    title: str
    authors: str
    language: str
    publisher: str | None = Field(None)
    series: str | None = Field(None)
    description: str | None = Field(None)
    pages: str | None = Field(None)
    year: str | None = Field(None)
    filepaths: list[str] = Field(..., min_length=1)
    source: AvailableSources  # Source for metadata and uploading.


class UploadedFileInfo(BaseModel):
    file_path: str
    available_at: str | None  # URL at which the file is available for moderation.


class UploadMetadataElements(BaseModel):
    title: WebElement
    authors: WebElement
    series: WebElement
    description: WebElement
    publisher: WebElement
    pages: WebElement
    language: Select

    class Config:
        arbitrary_types_allowed = True
