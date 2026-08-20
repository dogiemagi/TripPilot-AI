import re
from typing import Any
from pydantic import ValidationError


INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+|prior\s+)?instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"disregard\s+safety\s+guidelines",
    r"dump\s+database",
    r"drop\s+table",
]


class Guardrails:
    @staticmethod
    def validate_input(text: str) -> tuple[bool, str | None]:
        if not text or len(text.strip()) == 0:
            return False, "Input cannot be empty."
        if len(text) > 4000:
            return False, "Input exceeds maximum length of 4,000 characters."

        low_text = text.lower()
        for pat in INJECTION_PATTERNS:
            if re.search(pat, low_text):
                return False, "Input flagged by safety guardrails for potential instruction override."

        return True, None

    @staticmethod
    def sanitize_output(output_text: str) -> str:
        # Enforce that no simulated transaction IDs or credit card asks are displayed
        cleaned = re.sub(r"(?:fake_txn_\w+|booking_confirmed_live_\w+)", "[Booking Hold Placeholder]", output_text)
        return cleaned
