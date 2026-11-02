from datetime import UTC, date, datetime, timedelta, timezone, tzinfo

from sqlalchemy.orm import Session

# Pakistan has used UTC+5 with no DST since 2009. zoneinfo would need the tzdata
# package on Windows, which we are not adding.
KARACHI: tzinfo = timezone(timedelta(hours=5), name="Asia/Karachi")


def now_utc() -> datetime:
    return datetime.now(UTC)


def today_karachi(at: datetime | None = None) -> date:
    return (at or now_utc()).astimezone(KARACHI).date()


def karachi_day_range(day: date) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end, stored as UTC instants."""
    start_local = datetime(day.year, day.month, day.day, tzinfo=KARACHI)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def as_karachi_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(KARACHI).date()


def db_day_range(db: Session, day: date) -> tuple[datetime, datetime]:
    """SQLite drops time zone info, so comparisons must use naive UTC there."""
    start, end = karachi_day_range(day)
    if db.get_bind().dialect.name != "postgresql":
        return start.replace(tzinfo=None), end.replace(tzinfo=None)
    return start, end
