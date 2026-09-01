"""Tests for ticket dispatch scheduling.

The module exists so that `priority:low` cannot quietly start work in the
middle of a Princeton working day, so the properties worth pinning are the ones
that would let it: the daylight-saving offset, the two window boundaries, and
which label wins when several are attached.

The daylight-saving cases are the load-bearing ones. Both are 13:00 UTC, and a
fixed -05:00 offset -- the obvious wrong implementation -- reads both as 08:00
local and dispatches both. Only a zone-aware implementation sees 09:00 EDT in
July and holds.
"""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from infra.schedule import (
    dispatchable,
    explain,
    main,
    priority_of,
    within_working_hours,
)

# 13:00 UTC is 08:00 EST in January and 09:00 EDT in July.
WINTER_MORNING = datetime(2026, 1, 2, 13, 0, tzinfo=UTC)
SUMMER_MORNING = datetime(2026, 7, 1, 13, 0, tzinfo=UTC)


def test_daylight_saving_moves_the_window() -> None:
    assert not within_working_hours(WINTER_MORNING), "08:00 EST is before the window"
    assert within_working_hours(SUMMER_MORNING), "09:00 EDT is inside it"

    assert dispatchable("low", WINTER_MORNING)
    assert not dispatchable("low", SUMMER_MORNING)


@pytest.mark.parametrize(
    ("local_hour", "inside"),
    [(8, False), (9, True), (16, True), (17, False), (23, False)],
)
def test_the_window_is_half_open(local_hour: int, inside: bool) -> None:
    now = datetime(2026, 1, 2, local_hour, 0, tzinfo=ZoneInfo("America/New_York"))
    assert within_working_hours(now) is inside


def test_high_and_medium_ignore_the_window() -> None:
    for priority in ("high", "medium"):
        assert dispatchable(priority, SUMMER_MORNING)
        assert dispatchable(priority, WINTER_MORNING)


def test_the_most_urgent_label_wins_and_no_label_means_low() -> None:
    assert priority_of(["approved", "module:sim"]) == "low"
    assert priority_of(["priority:low", "priority:high"]) == "high"
    assert priority_of(["priority:medium", "priority:low"]) == "medium"
    assert priority_of(["priority:urgent"]) == "low", "an unknown priority is not high"


def test_filter_selects_only_the_tickets_that_may_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    tickets = [
        {"number": 1, "labels": ["priority:low"]},
        {"number": 2, "labels": ["priority:high"]},
        {"number": 3, "labels": []},
        {"number": 4, "labels": ["priority:medium"]},
    ]
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(tickets)))

    assert main(["--now", SUMMER_MORNING.isoformat(), "filter"]) == 0

    assert json.loads(capsys.readouterr().out) == [2, 4]


def test_decide_prints_a_verdict_and_a_reason(
    capsys: pytest.CaptureFixture[str],
) -> None:
    when = ["--now", SUMMER_MORNING.isoformat()]

    assert main([*when, "decide", "--labels", "priority:low,approved"]) == 0
    assert capsys.readouterr().out.strip() == "hold"

    assert main([*when, "decide", "--labels", "priority:high"]) == 0
    assert capsys.readouterr().out.strip() == "run"

    assert main([*when, "decide", "--labels", "", "--explain"]) == 0
    reason = capsys.readouterr().out.strip()
    assert "priority:low" in reason, "no label means low, and the reason should say so"
    assert "09:00-17:00" in reason


def test_a_naive_timestamp_is_read_as_utc(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--now", "2026-07-01T13:00:00", "decide", "--labels", ""]) == 0
    assert capsys.readouterr().out.strip() == "hold"


def test_explain_names_the_next_opportunity_rather_than_a_time() -> None:
    assert "next sweep" in explain("medium", SUMMER_MORNING)
    assert "immediately" in explain("high", SUMMER_MORNING)
