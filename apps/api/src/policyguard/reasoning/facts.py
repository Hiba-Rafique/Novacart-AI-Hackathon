from __future__ import annotations

import re
from datetime import date

_CONTACT_DATE = re.compile(
    r"\bcontact[\s_-]+date\s*(?:(?:is|was)\b|[:=])?\s*"
    r"(?P<date>\d{4}-\d{2}-\d{2}|today|yesterday|tomorrow|last\s+week|next\s+week)\b",
    re.IGNORECASE,
)
_DATE_ONLY = re.compile(r"\s*(\d{4}-\d{2}-\d{2})[.!]?\s*")


def extract_contact_date(question: str, *, awaiting_contact_date: bool = False) -> date | None:
    """Read explicitly labelled dates without mistaking purchase dates for contact dates."""
    values = [match.group("date") for match in _CONTACT_DATE.finditer(question)]
    if not values and awaiting_contact_date:
        match = _DATE_ONLY.fullmatch(question)
        if match:
            values = [match.group(1)]
    try:
        dates = {date.fromisoformat(value) for value in values}
    except ValueError as exc:
        raise ValueError("What is your valid contact date in YYYY-MM-DD format?") from exc
    if len(dates) > 1:
        raise ValueError("You supplied different contact dates. Which one should I use?")
    return next(iter(dates), None)
