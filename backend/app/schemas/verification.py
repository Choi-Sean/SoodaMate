from pydantic import BaseModel, EmailStr, Field


class VerificationStartRequest(BaseModel):
    kind: str = Field(pattern="^(work|school)$")
    email: EmailStr


class VerificationConfirmRequest(BaseModel):
    kind: str = Field(pattern="^(work|school)$")
    code: str = Field(min_length=6, max_length=6)
