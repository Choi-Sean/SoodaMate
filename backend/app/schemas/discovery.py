import uuid

from pydantic import BaseModel

from app.schemas.profile import PhotoOut


class CandidateOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    age: int
    gender: str
    bio: str | None
    photos: list[PhotoOut]
    distance_km: float | None = None
    superliked_me: bool = False
    # Extended profile fields shown on the expanded (scroll-down) card view
    # — same free-text category strings as Profile itself (see models/
    # profile.py's comment on why these aren't enums).
    height_cm: int | None = None
    occupation: str | None = None
    education: str | None = None
    hometown: str | None = None
    race_ethnicity: str | None = None
    religion: str | None = None
    political_view: str | None = None
    smoking: str | None = None
    cannabis: str | None = None
    exercise_frequency: str | None = None
    relationship_goal: str | None = None
    wants_kids: str | None = None
    has_kids: str | None = None
    interests: list[str] = []
    languages: list[str] = []
    verified_badge: str | None = None
