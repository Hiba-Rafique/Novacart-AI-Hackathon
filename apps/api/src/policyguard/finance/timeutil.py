from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal, Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def today(self) -> date: ...


class SystemClock:
    def __init__(self, timezone: ZoneInfo) -> None:
        self._timezone = timezone

    def today(self) -> date:
        return datetime.now(self._timezone).date()


class FixedClock:
    def __init__(self, today: date) -> None:
        self._today = today

    def today(self) -> date:
        return self._today


@dataclass(frozen=True)
class DateResolution:
    contact_date: date
    source: Literal["explicit", "system"]


def resolve_contact_date(
    explicit: date | None,
    clock: Clock,
) -> DateResolution:
    if explicit is not None:
        return DateResolution(contact_date=explicit, source="explicit")
    return DateResolution(contact_date=clock.today(), source="system")


def add_days(start: date, days: int) -> date:
    return start + timedelta(days=days)


def is_within_days(start: date, request_date: date, days: int) -> bool:
    if days < 0:
        raise ValueError("days must not be negative")
    return request_date <= add_days(start, days)


def add_business_days(start: date, days: int) -> date:
    if days < 0:
        raise ValueError("days must not be negative")
    current = start
    remaining = days
    while remaining:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def count_business_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("end must not be before start")
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            count += 1
    return count


def add_months(start: date, months: int) -> date:
    if months < 0:
        raise ValueError("months must not be negative")
    total = start.month - 1 + months
    year = start.year + total // 12
    month = total % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def full_months_between(start: date, end: date) -> int:
    if end < start:
        return 0
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if months <= 0:
        return 0
    if add_months(start, months) > end:
        months -= 1
    return months
