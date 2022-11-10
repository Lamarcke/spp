from enum import Enum

from pydantic import BaseModel, Field

from scrapers_preservation.models.uploader_models import ValidTopics


class ElivrosMetadata(BaseModel):
    topic: ValidTopics
    title: str
    authors: str
    language: str = Field("Portuguese")
    series: str | None = Field(None)
    description: str | None = Field(None)
    pages: str | None = Field(None)

