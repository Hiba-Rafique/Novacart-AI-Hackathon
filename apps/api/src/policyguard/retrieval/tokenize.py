from __future__ import annotations

import re

_TOKEN = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*")

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "by",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "has",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "its",
    "may",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "please",
    "should",
    "so",
    "that",
    "the",
    "their",
    "them",
    "this",
    "to",
    "was",
    "we",
    "what",
    "when",
    "where",
    "which",
    "who",
    "will",
    "with",
    "would",
    "you",
    "your",
}

_SYNONYMS = {
    "cancel": ("cancellation", "cancelled", "canceled"),
    "cancellation": ("cancel", "cancelled", "canceled"),
    "cod": ("cash", "delivery"),
    "courier": ("delivery", "dispatch", "parcel"),
    "credit": ("refund", "wallet"),
    "delivery": ("shipping", "dispatch", "courier", "parcel"),
    "discount": ("promo", "code", "coupon"),
    "dispatch": ("delivery", "shipping", "courier"),
    "fee": ("charge", "cost", "shipping"),
    "gst": ("tax", "taxes"),
    "guarantee": ("warranty",),
    "international": ("abroad", "overseas"),
    "parcel": ("delivery", "dispatch", "courier"),
    "promo": ("discount", "code", "coupon"),
    "refund": ("return", "refunded", "money"),
    "return": ("refund", "returns", "returned"),
    "shipping": ("delivery", "dispatch", "courier", "fee"),
    "tax": ("gst",),
    "warranty": ("guarantee", "repair", "replacement"),
}


def tokenize(text: str, *, expand: bool = False) -> list[str]:
    tokens = [
        token
        for token in _TOKEN.findall(text.lower())
        if token not in _STOPWORDS and len(token) > 1
    ]
    if not expand:
        return tokens

    expanded = list(tokens)
    for token in tokens:
        expanded.extend(_SYNONYMS.get(token, ()))
    return expanded
