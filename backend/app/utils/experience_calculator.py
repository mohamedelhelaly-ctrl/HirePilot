"""
Experience Calculator

Pure Python utility for calculating total professional experience from
a list of roles extracted by the LLM.

Philosophy: LLM extracts, Python calculates.
The LLM is responsible for pulling out role titles, companies, dates, and
employment types. This module is responsible for all the math — date parsing,
type filtering, overlap resolution, and total calculation.

Filtering rules (what counts toward total experience):
    ✅ full_time  — counted
    ✅ freelance  — counted
    ❌ internship — excluded
    ❌ part_time  — excluded
    ❌ volunteer  — excluded
    ❌ trainer    — excluded
    ❌ instructor — excluded
    ❌ unknown    — excluded (conservative default)

Overlap handling:
    Concurrent roles (e.g. a full-time job overlapping with a freelance
    project) are merged so the same calendar period is only counted once.
    Adjacent months (no gap) are also merged.
"""

import re
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Employment types that count toward total professional experience
_COUNTED_TYPES = {"full_time", "freelance"}

# Employment types explicitly excluded
_EXCLUDED_TYPES = {"internship", "part_time", "volunteer", "trainer", "instructor"}


def _parse_date(date_str: str, current_date: datetime) -> datetime:
    """
    Parse a date string from an LLM-extracted role into a datetime.

    Supported input formats:
        "3/2024" or "03/2024"     → March 2024
        "March 2024" / "Mar 2024" → March 2024
        "2024-03" / "2024/03"     → March 2024
        "2024"                    → January 2024 (year only — assume start of year)
        "Present" / "Current" / "Now" / "Ongoing" → current_date

    Returns:
        datetime set to the first day of the resolved month.

    Raises:
        ValueError: if the string cannot be parsed.
    """
    date_str = str(date_str).strip()

    if date_str.lower() in {"present", "current", "now", "ongoing"}:
        return current_date

    # MM/YYYY or M/YYYY
    m = re.match(r'^(\d{1,2})/(\d{4})$', date_str)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid month {month} in '{date_str}'")
        return datetime(year, month, 1)

    # Abbreviated month name: "Jan 2024"
    try:
        return datetime.strptime(date_str, "%b %Y")
    except ValueError:
        pass

    # Full month name: "January 2024"
    try:
        return datetime.strptime(date_str, "%B %Y")
    except ValueError:
        pass

    # YYYY-MM or YYYY/MM
    m = re.match(r'^(\d{4})[-/](\d{1,2})$', date_str)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid month {month} in '{date_str}'")
        return datetime(year, month, 1)

    # Year only: "2022"
    m = re.match(r'^(\d{4})$', date_str)
    if m:
        return datetime(int(m.group(1)), 1, 1)

    raise ValueError(f"Cannot parse date: '{date_str}'")


def _duration_months(start: datetime, end: datetime) -> int:
    """
    Inclusive month count between two dates.

    Both the start month and the end month are counted as worked.
    Formula: (end_year - start_year) * 12 + (end_month - start_month) + 1

    Examples:
        Mar 2024 → Mar 2024 = 1 month
        Mar 2024 → Oct 2024 = 8 months
        Nov 2022 → Feb 2024 = 16 months
    """
    if end < start:
        raise ValueError(
            f"End date {end.strftime('%m/%Y')} is before start {start.strftime('%m/%Y')}"
        )
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1
    return max(1, months)


def _merge_periods(periods: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    """
    Merge overlapping or adjacent date ranges into non-overlapping spans.

    Algorithm:
        1. Sort by start date.
        2. Walk forward; if the next period starts on or before the current
           end (or in the immediately following month), extend the current
           period rather than starting a new one.
        3. Save and advance when a genuine gap is found.

    Adjacent = next period starts in the month immediately after current end.
    """
    if not periods:
        return []

    sorted_periods = sorted(periods, key=lambda p: p[0])
    merged = []
    cur_start, cur_end = sorted_periods[0]

    for start, end in sorted_periods[1:]:
        # Check adjacency: start falls in the month right after cur_end
        adjacent = (
            (start.year == cur_end.year and start.month == cur_end.month + 1)
            or (start.year == cur_end.year + 1 and cur_end.month == 12 and start.month == 1)
        )
        if start <= cur_end or adjacent:
            cur_end = max(cur_end, end)
        else:
            merged.append((cur_start, cur_end))
            cur_start, cur_end = start, end

    merged.append((cur_start, cur_end))
    return merged


def calculate_experience(
    roles: list[dict],
    current_date: Optional[datetime] = None,
) -> float:
    """
    Calculate total professional experience in years from a list of roles.

    Args:
        roles: List of role dicts as returned by the LLM extraction prompt.
               Each dict should have:
                   title      (str)
                   company    (str)
                   start_date (str)  — parseable date string
                   end_date   (str)  — parseable date string or "Present"
                   type       (str)  — employment type

        current_date: Reference date for "Present" roles. Defaults to now.

    Returns:
        Total years of professional experience (float, 1 decimal place).
        Returns 0.0 if no qualifying roles can be parsed.
    """
    now = current_date or datetime.now()

    periods: list[tuple[datetime, datetime]] = []

    for role in roles:
        employment_type = str(role.get("type", "")).lower().strip()

        # Skip non-professional types
        if employment_type not in _COUNTED_TYPES:
            if employment_type in _EXCLUDED_TYPES:
                logger.debug(
                    f"[ExperienceCalculator] Excluded '{role.get('title')}' "
                    f"at '{role.get('company')}' — type='{employment_type}'"
                )
            else:
                logger.debug(
                    f"[ExperienceCalculator] Excluded '{role.get('title')}' "
                    f"at '{role.get('company')}' — unknown type='{employment_type}'"
                )
            continue

        start_str = role.get("start_date", "")
        end_str   = role.get("end_date",   "")

        if not start_str or not end_str:
            logger.warning(
                f"[ExperienceCalculator] Missing dates for '{role.get('title')}' "
                f"at '{role.get('company')}' — skipping"
            )
            continue

        try:
            start = _parse_date(start_str, now)
            end   = _parse_date(end_str,   now)
        except ValueError as exc:
            logger.warning(
                f"[ExperienceCalculator] Date parse error for "
                f"'{role.get('title')}' at '{role.get('company')}': {exc} — skipping"
            )
            continue

        if end < start:
            logger.warning(
                f"[ExperienceCalculator] End before start for "
                f"'{role.get('title')}' at '{role.get('company')}' — skipping"
            )
            continue

        periods.append((start, end))

    if not periods:
        return 0.0

    merged = _merge_periods(periods)
    total_months = sum(_duration_months(s, e) for s, e in merged)
    return round(total_months / 12, 1)