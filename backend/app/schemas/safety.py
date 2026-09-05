import uuid

from pydantic import BaseModel, Field


class BlockRequest(BaseModel):
    user_id: uuid.UUID


class ReportRequest(BaseModel):
    user_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=100)
    detail: str | None = Field(default=None, max_length=1000)
