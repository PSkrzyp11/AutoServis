import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.services.availability import (
    AvailabilityRequest,
    BusyInterval,
    OpeningWindow,
    compute_available_slots,
    local_day_bounds,
)

WARSAW = ZoneInfo("Europe/Warsaw")
DAY = date(2026, 12, 7)
FIRST_BAY = uuid.uuid4()
SECOND_BAY = uuid.uuid4()
LONG_AGO = datetime(2000, 1, 1, tzinfo=UTC)
MORNING_WINDOW = OpeningWindow(time(8), time(10))


def local(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute), tzinfo=WARSAW).astimezone(UTC)


def request(
    *,
    day: date = DAY,
    duration_minutes: int = 60,
    bay_ids: tuple[uuid.UUID, ...] = (FIRST_BAY,),
    busy: tuple[BusyInterval, ...] = (),
    earliest_start: datetime = LONG_AGO,
    is_closed: bool = False,
    window: OpeningWindow | None = MORNING_WINDOW,
) -> AvailabilityRequest:
    return AvailabilityRequest(
        day=day,
        timezone=WARSAW,
        opening_window=window,
        is_closed=is_closed,
        duration=timedelta(minutes=duration_minutes),
        bay_ids=bay_ids,
        busy_intervals=busy,
        earliest_start=earliest_start,
    )


def test_slots_cover_opening_hours_every_fifteen_minutes() -> None:
    slots = compute_available_slots(request())

    assert [slot.start_at for slot in slots] == [
        local(DAY, 8, 0),
        local(DAY, 8, 15),
        local(DAY, 8, 30),
        local(DAY, 8, 45),
        local(DAY, 9, 0),
    ]
    assert slots[-1].end_at == local(DAY, 10, 0)


def test_service_longer_than_opening_hours_has_no_slots() -> None:
    assert compute_available_slots(request(duration_minutes=180)) == []


def test_closed_day_and_missing_hours_or_bays_have_no_slots() -> None:
    assert compute_available_slots(request(is_closed=True)) == []
    assert compute_available_slots(request(window=None)) == []
    assert compute_available_slots(request(bay_ids=())) == []


def test_busy_bay_blocks_overlapping_slots_only() -> None:
    busy = (BusyInterval(FIRST_BAY, local(DAY, 8, 30), local(DAY, 9, 0)),)

    slots = compute_available_slots(request(duration_minutes=30, busy=busy))

    assert [slot.start_at for slot in slots] == [
        local(DAY, 8, 0),
        local(DAY, 9, 0),
        local(DAY, 9, 15),
        local(DAY, 9, 30),
    ]


def test_second_bay_keeps_slot_available_and_reports_free_bays() -> None:
    busy = (BusyInterval(FIRST_BAY, local(DAY, 8, 0), local(DAY, 10, 0)),)

    slots = compute_available_slots(request(bay_ids=(FIRST_BAY, SECOND_BAY), busy=busy))

    assert len(slots) == 5
    assert all(slot.free_bay_ids == (SECOND_BAY,) for slot in slots)


def test_slots_before_earliest_start_are_skipped() -> None:
    slots = compute_available_slots(request(earliest_start=local(DAY, 8, 40)))

    assert [slot.start_at for slot in slots] == [local(DAY, 8, 45), local(DAY, 9, 0)]


def test_daylight_saving_time_changes_shift_utc_offsets() -> None:
    spring_day = date(2027, 3, 28)
    autumn_day = date(2026, 10, 25)

    spring_slots = compute_available_slots(request(day=spring_day))
    autumn_slots = compute_available_slots(request(day=autumn_day))

    assert spring_slots[0].start_at == datetime(2027, 3, 28, 6, 0, tzinfo=UTC)
    assert autumn_slots[0].start_at == datetime(2026, 10, 25, 7, 0, tzinfo=UTC)


def test_local_day_bounds_follow_time_zone() -> None:
    start, end = local_day_bounds(date(2027, 3, 28), WARSAW)

    assert start == datetime(2027, 3, 27, 23, 0, tzinfo=UTC)
    assert end == datetime(2027, 3, 28, 22, 0, tzinfo=UTC)
    assert end - start == timedelta(hours=23)
