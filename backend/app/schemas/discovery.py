import uuid

from pydantic import BaseModel

from app.schemas.profile import PhotoOut


class CandidateOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    age: int
    bio: str | None
    photos: list[PhotoOut]
    distance_km: float | None = None
    superliked_me: bool = False
