from pydantic import BaseModel, Field


class InquiryCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=4000)
