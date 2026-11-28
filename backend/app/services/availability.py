import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

SLOT_STEP = timedelta(minutes=15)


@dataclass(frozen=True)
class OpeningWindow:
    opens_at: time
    closes_at: time


@dataclass(frozen=True)
class BusyInterval:
    bay_id: uuid.UUID
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class AvailableSlot:
    start_at: datetime
    end_at: datetime
    free_bay_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class AvailabilityRequest:
    day: date
    timezone: ZoneInfo
    opening_window: OpeningWindow | None
    is_closed: bool
    duration: timedelta
    bay_ids: Sequence[uuid.UUID]
    busy_intervals: Sequence[BusyInterval]
    earliest_start: datetime


def local_day_bounds(day: date, timezone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone).astimezone(UTC)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=timezone).astimezone(UTC)
    return start, end


def overlaps(interval: BusyInterval, start_at: datetime, end_at: datetime) -> bool:
    return interval.start_at < end_at and interval.end_at > start_at


def free_bays(
    bay_ids: Sequence[uuid.UUID],
    busy_intervals: Sequence[BusyInterval],
    start_at: datetime,
    end_at: datetime,
) -> tuple[uuid.UUID, ...]:
    busy_bay_ids = {
        interval.bay_id for interval in busy_intervals if overlaps(interval, start_at, end_at)
    }
    return tuple(bay_id for bay_id in bay_ids if bay_id not in busy_bay_ids)


def candidate_local_starts(day: date, window: OpeningWindow, duration: timedelta) -> list[datetime]:
    opens_at = datetime.combine(day, window.opens_at)
    latest_start = datetime.combine(day, window.closes_at) - duration
    starts: list[datetime] = []
    current = opens_at
    while current <= latest_start:
        starts.append(current)
        current += SLOT_STEP
    return starts


def compute_available_slots(request: AvailabilityRequest) -> list[AvailableSlot]:
    if request.is_closed or request.opening_window is None or not request.bay_ids:
        return []
    slots: list[AvailableSlot] = []
    for local_start in candidate_local_starts(
        request.day,
        request.opening_window,
        request.duration,
    ):
        start_at = local_start.replace(tzinfo=request.timezone).astimezone(UTC)
        end_at = (local_start + request.duration).replace(tzinfo=request.timezone).astimezone(UTC)
        if start_at < request.earliest_start:
            continue
        available_bays = free_bays(request.bay_ids, request.busy_intervals, start_at, end_at)
        if available_bays:
            slots.append(
                AvailableSlot(start_at=start_at, end_at=end_at, free_bay_ids=available_bays)
            )
    return slots
