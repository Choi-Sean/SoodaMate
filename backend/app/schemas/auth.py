import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthRequest(BaseModel):
    id_token: str


class AppleAuthRequest(BaseModel):
    identity_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class PhoneAuthStartRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)


class PhoneAuthConfirmRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    code: str = Field(min_length=4, max_length=10)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID


class PhoneAuthResponse(TokenResponse):
    # Lets the client show a first-time welcome beat if it ever wants to —
    # RootNavigator itself doesn't need this, since routing new vs. existing
    # users is already handled by whether a Profile row exists.
    is_new_user: bool
