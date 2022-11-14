from pydantic import BaseModel, Field

from models.uploader_models import LibgenMetadata


class UploadHistoryEntry(BaseModel):
    uploaded_file: str
    available_at: str


class DownloadHistoryEntry(BaseModel):
    metadata: LibgenMetadata
    stored_at: list[str] = Field(..., min_length=1)
