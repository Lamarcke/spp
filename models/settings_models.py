from pydantic import BaseModel, Field


class SPPSettingsModel(BaseModel):

    max_downloads = Field(100)  # type: ignore
