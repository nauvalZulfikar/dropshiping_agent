from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")  # UTC+7

SALE_EVENTS = [
    "01-01",  # New Year
    "02-14",  # Valentine
    "04-10",  # Lebaran (approximate, update yearly)
    "05-02",  # Hari Pendidikan
    "08-17",  # HUT RI
    "10-10",  # 10.10 Harbolnas
    "11-11",  # 11.11 Harbolnas
    "12-12",  # 12.12 Harbolnas
    "12-25",  # Christmas
]


def now_wib() -> datetime:
    """Current datetime in WIB (UTC+7)."""
    return datetime.now(tz=WIB)


def days_to_next_sale_event() -> int:
    """
    Return integer number of days until the next major Indonesian sale event.
    """
    today = now_wib().date()
    year = today.year
    min_days = 366

    for event_str in SALE_EVENTS:
        month, day = map(int, event_str.split("-"))
        event_date = date(year, month, day)
        if event_date < today:
            # Try next year
            event_date = date(year + 1, month, day)
        delta = (event_date - today).days
        if delta < min_days:
            min_days = delta

    return min_days


def seasonal_index(reference_date: date | None = None) -> float:
    """
    Returns a seasonal multiplier (0.5–2.0) based on proximity to major sale events.
    Closer to an event → higher multiplier.
    """
    days = days_to_next_sale_event()
    if days <= 7:
        return 2.0
    if days <= 14:
        return 1.5
    if days <= 30:
        return 1.2
    return 1.0
