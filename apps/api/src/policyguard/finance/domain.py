from __future__ import annotations

from typing import Literal

Category = Literal[
    "electronics",
    "clothing",
    "grocery/perishables",
    "furniture/bulky",
    "personal care",
]
Region = Literal["metro", "rest_of_pakistan", "remote", "international"]
InternationalCountry = Literal["UAE", "UK", "USA"]

CATEGORY_ALIASES = {
    "electronics": "electronics",
    "electronic": "electronics",
    "clothing": "clothing",
    "clothes": "clothing",
    "grocery": "grocery/perishables",
    "groceries": "grocery/perishables",
    "grocery/perishables": "grocery/perishables",
    "perishables": "grocery/perishables",
    "furniture": "furniture/bulky",
    "furniture/bulky": "furniture/bulky",
    "bulky": "furniture/bulky",
    "personal care": "personal care",
    "personal-care": "personal care",
    "personalcare": "personal care",
}

REGION_ALIASES = {
    "metro": "metro",
    "metro city": "metro",
    "metro cities": "metro",
    "rest of pakistan": "rest_of_pakistan",
    "rest_of_pakistan": "rest_of_pakistan",
    "rop": "rest_of_pakistan",
    "remote": "remote",
    "remote area": "remote",
    "remote areas": "remote",
    "ajk": "remote",
    "gilgit-baltistan": "remote",
    "international": "international",
}

INTERNATIONAL_ALIASES = {
    "uae": "UAE",
    "united arab emirates": "UAE",
    "uk": "UK",
    "united kingdom": "UK",
    "usa": "USA",
    "us": "USA",
    "united states": "USA",
}


class PolicyInputError(ValueError):
    pass


class MissingFactError(PolicyInputError):
    pass


class NotApplicableError(PolicyInputError):
    pass


def normalize_category(value: str) -> Category:
    try:
        return CATEGORY_ALIASES[value.strip().lower()]  # type: ignore[return-value]
    except KeyError as exc:
        raise PolicyInputError(f"unsupported category: {value!r}") from exc


def normalize_region(value: str) -> Region:
    try:
        return REGION_ALIASES[value.strip().lower()]  # type: ignore[return-value]
    except KeyError as exc:
        raise PolicyInputError(f"unsupported region: {value!r}") from exc


def normalize_country(value: str) -> InternationalCountry:
    try:
        return INTERNATIONAL_ALIASES[value.strip().lower()]  # type: ignore[return-value]
    except KeyError as exc:
        raise PolicyInputError(f"unsupported international destination: {value!r}") from exc


def is_bulky(category: str) -> bool:
    return normalize_category(category) == "furniture/bulky"
