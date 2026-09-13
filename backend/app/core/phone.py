import re

from fastapi import HTTPException, status

# E.164: '+' then 8-15 digits. The client is responsible for turning a
# local-format number into this via a country picker — this is just a sanity
# gate before we hand it to Twilio, not a full validation.
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_e164(phone_number: str) -> str:
    if not E164_PATTERN.match(phone_number):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "phone_number must be in E.164 format, e.g. +821012345678")
    return phone_number
