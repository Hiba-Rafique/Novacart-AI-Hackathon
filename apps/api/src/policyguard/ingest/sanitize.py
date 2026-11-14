from __future__ import annotations

import re

from .models import QuarantinedLine

_HTML_COMMENT = re.compile(r"^\s*<!--.*-->\s*$")
_INJECTION_PATTERNS = (
    re.compile(r"\bsystem\s+override\b", re.IGNORECASE),
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\breveal\s+your\s+system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\binstruction\s+for\s+(ai\s+)?assistants?\b", re.IGNORECASE),
    re.compile(r"\binternal\s+note\s+for\s+customer\s+service\s+bots\b", re.IGNORECASE),
)


def sanitize_line(
    file_name: str,
    line_number: int,
    line: str,
) -> tuple[str | None, QuarantinedLine | None]:
    if _HTML_COMMENT.match(line):
        return None, QuarantinedLine(
            file_name=file_name,
            line_number=line_number,
            reason="html_comment",
        )

    for pattern in _INJECTION_PATTERNS:
        if pattern.search(line):
            return None, QuarantinedLine(
                file_name=file_name,
                line_number=line_number,
                reason="prompt_injection",
            )

    return line, None
