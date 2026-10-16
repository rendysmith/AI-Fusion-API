"""Error mapping service for user-friendly error messages."""

import logging

logger = logging.getLogger(__name__)

ERROR_RULES = [
    (
        ["photorealistic people", "real person", "human face"],
        "This model prohibits uploading images of real people (photorealism). "
        "Please use generated or stylized faces.",
    ),
    (
        ["nudity", "sexuality", "erotic", "nsfw", "sexual"],
        "Request blocked by safety filter (18+ themes, nudity). "
        "Please change your prompt or image.",
    ),
    (
        ["cameo", "celebrity", "public figure", "famous"],
        "Mentioning specific individuals or celebrities without permission "
        "is prohibited.",
    ),
    (
        ["third-party", "copyright", "intellectual property"],
        "Request rejected due to similarity with copyrighted content.",
    ),
    (
        ["upload image violation", "image_moderation"],
        "Uploaded image failed the neural network safety check. "
        "Please try a different photo.",
    ),
    (
        ["content policies", "guardrails", "moderation", "safety",
         "censorship", "policy violation"],
        "Request blocked by safety guardrails. "
        "Please rephrase your request more neutrally.",
    ),
    (
        ["timeout", "timed out"],
        "Generation timed out. The service is overloaded, please try later.",
    ),
    (
        ["500", "502", "503", "504", "429", "connection error", "connector"],
        "Neural network servers are overloaded or unavailable. "
        "Please try again in a few minutes.",
    ),
]

MSG_UNKNOWN = (
    "A technical error occurred. We are looking into it. "
    "Please try different parameters."
)


def get_user_friendly_error(error: Exception) -> str:
    """Convert a technical provider error into a user-friendly message."""
    error_str = str(error).lower()

    for keywords, user_message in ERROR_RULES:
        if any(key in error_str for key in keywords):
            return user_message

    if "400" in error_str:
        return "Invalid request parameters. Possible error in prompt or settings."

    return MSG_UNKNOWN
