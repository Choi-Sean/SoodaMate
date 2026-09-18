MBTI_TYPES: tuple[str, ...] = (
    "ISTJ", "ISFJ", "INFJ", "INTJ",
    "ISTP", "ISFP", "INFP", "INTP",
    "ESTP", "ESFP", "ENFP", "ENTP",
    "ESTJ", "ESFJ", "ENFJ", "ENTJ",
)

# Each type's single best-match partner, per the commonly-circulated popular
# theory: same information-processing preferences (S/N and T/F — how you take
# in the world and make decisions) but opposite energy/lifestyle preferences
# (E/I and J/P) — shared core values, complementary pace. Deliberately a 1:1
# mutual pairing (A's match is B iff B's match is A) rather than a fuzzier
# "compatible with several types" table — simpler to reason about, and a
# clean single "your type" is a better dating-app result than a list.
MBTI_COMPATIBILITY: dict[str, str] = {
    "ISTJ": "ESTP", "ESTP": "ISTJ",
    "ISFJ": "ESFP", "ESFP": "ISFJ",
    "INFJ": "ENFP", "ENFP": "INFJ",
    "INTJ": "ENTP", "ENTP": "INTJ",
    "ISTP": "ESTJ", "ESTJ": "ISTP",
    "ISFP": "ESFJ", "ESFJ": "ISFP",
    "INFP": "ENFJ", "ENFJ": "INFP",
    "INTP": "ENTJ", "ENTJ": "INTP",
}


def compatible_types(mbti: str | None) -> list[str]:
    match = MBTI_COMPATIBILITY.get((mbti or "").upper())
    return [match] if match else []
