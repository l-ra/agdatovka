"""Pure, explicit retention-clock oracle for QA (not a legal policy)."""
from dataclasses import dataclass
from datetime import date, timedelta

@dataclass(frozen=True)
class RetentionDecision:
    eligible_on: date
    eligible: bool
    reason: str

def add_reference_days(start: date, days: int, holidays: set[date] = frozenset()) -> date:
    if days < 0:
        raise ValueError("days must be non-negative")
    current, counted = start, 0
    while counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            counted += 1
    return current

def reference_retention(kind: str, delivered_on: date, at: date, *, legal_hold: bool = False, holidays: set[date] = frozenset()) -> RetentionDecision:
    days = {"ordinary": 90, "system": 100}.get(kind)
    if days is None:
        raise ValueError(f"unsupported retention class: {kind}")
    eligible_on = add_reference_days(delivered_on, days, holidays)
    return RetentionDecision(eligible_on, at >= eligible_on and not legal_hold, "legal_hold" if legal_hold else "reference_profile")
