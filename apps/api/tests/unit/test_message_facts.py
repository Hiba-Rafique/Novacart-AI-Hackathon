from datetime import date

import pytest

from policyguard.reasoning.facts import extract_contact_date


@pytest.mark.parametrize(
    "question",
    [
        "My contact date is 2027-03-01.",
        "CONTACT DATE: 2027-03-01",
        "contact_date=2027-03-01",
        "Delivery date is 2026-12-15. Contact date was 2027-03-01.",
    ],
)
def test_extracts_labelled_contact_date(question: str) -> None:
    assert extract_contact_date(question) == date(2027, 3, 1)


@pytest.mark.parametrize(
    "question",
    [
        "My order date is 2027-03-01.",
        "My delivery date is 2027-03-01.",
        "My warranty claim date is 2027-03-01.",
        "2027-03-01",
    ],
)
def test_unlabelled_or_other_event_dates_are_not_contact_dates(question: str) -> None:
    assert extract_contact_date(question) is None


def test_date_only_reply_is_accepted_when_contact_date_was_requested() -> None:
    assert extract_contact_date("2027-03-01", awaiting_contact_date=True) == date(2027, 3, 1)
