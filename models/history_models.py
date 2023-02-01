from pydantic import BaseModel, Field

from models.uploader_models import LibgenMetadata


class HistoryEntry(BaseModel):
    entry_id: int = Field(...)
    metadata: LibgenMetadata = Field(...)
    file_path: str = Field(...)
