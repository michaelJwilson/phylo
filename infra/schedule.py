"""Decide when an approved ticket is allowed to start.

The priority labels only mean something if something enforces them, and a
workflow triggered by a comment runs immediately by definition. So `/approve`
records approval and this module decides whether the work starts now or waits
for a scheduled sweep to pick it up.

The policy is `infra/CLAUDE.md`'s:

* ``priority:high`` runs immediately.
* ``priority:medium`` runs at the next sweep, when tokens have refreshed.
* ``priority:low`` runs outside 09:00-17:00 Princeton time, and is the default
  for any ticket carrying no priority label.

Princeton observes daylight saving, so the window is evaluated in
``America/New_York`` rather than against a fixed UTC offset: a fixed -05:00
would put the summer window an hour wrong and let low-priority work start in
the middle of a working morning.

The window is literal, with no weekday qualifier, because the policy it
implements has none. Saturday at noon is inside working hours.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

#: Priorities, most urgent first. Anything else is treated as the default.
PRIORITIES: tuple[str, ...] = ("high", "medium", "low")
DEFAULT_PRIORITY = "low"
LABEL_PREFIX = "priority:"

#: Princeton, NJ. Named rather than offset so daylight saving is handled.
ZONE = ZoneInfo("America/New_York")
WORKING_START = time(9, 0)
WORKING_END = time(17, 0)


def priority_of(labels: Iterable[str]) -> str:
    """Return the priority a ticket's labels select, defaulting to ``low``.

    The most urgent label wins if several are attached, which is the reading
    that cannot silently downgrade work someone marked urgent.
    """
    attached = {
        label.removeprefix(LABEL_PREFIX)
        for label in labels
        if label.startswith(LABEL_PREFIX)
    }
    for priority in PRIORITIES:
        if priority in attached:
            return priority
    return DEFAULT_PRIORITY


def within_working_hours(now: datetime) -> bool:
    """Is ``now`` inside 09:00-17:00 Princeton time?

    The interval is half-open: 09:00 is inside it, 17:00 is not.
    """
    local = now.astimezone(ZONE).timetz()
    return WORKING_START <= local.replace(tzinfo=None) < WORKING_END


def dispatchable(priority: str, now: datetime) -> bool:
    """May a ticket at ``priority`` start at ``now``?"""
    if priority == "high":
        return True
    if priority == "medium":
        return True
    return not within_working_hours(now)


def explain(priority: str, now: datetime) -> str:
    """One sentence for the ticket thread, saying what happens and when."""
    local = now.astimezone(ZONE)
    stamp = local.strftime("%H:%M %Z")
    if priority == "high":
        return "`priority:high` starts immediately."
    if priority == "medium":
        return (
            "`priority:medium` starts at the next sweep of the ticket queue, "
            "when tokens have refreshed."
        )
    if dispatchable(priority, now):
        return f"`priority:low` starts now: it is {stamp}, outside 09:00-17:00."
    return (
        f"`priority:low` waits for a sweep outside 09:00-17:00 Princeton time; "
        f"it is {stamp}."
    )


def _now(argument: str | None) -> datetime:
    if argument is None:
        return datetime.now(tz=UTC)
    parsed = datetime.fromisoformat(argument)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _labels(argument: str) -> list[str]:
    return [label.strip() for label in argument.split(",") if label.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ticket dispatch scheduling.")
    parser.add_argument(
        "--now", help="ISO-8601 instant to evaluate against (default: now, UTC)"
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    decide = subcommands.add_parser("decide", help="run or hold, for one ticket")
    decide.add_argument("--labels", default="", help="comma-separated label names")
    decide.add_argument(
        "--explain", action="store_true", help="print the reason, not the verdict"
    )

    subcommands.add_parser(
        "filter",
        help="read [{number, labels}] on stdin, print the numbers that may start",
    )

    args = parser.parse_args(argv)
    now = _now(args.now)

    if args.command == "decide":
        priority = priority_of(_labels(args.labels))
        if args.explain:
            print(explain(priority, now))
        else:
            print("run" if dispatchable(priority, now) else "hold")
        return 0

    tickets = json.load(sys.stdin)
    ready = [
        ticket["number"]
        for ticket in tickets
        if dispatchable(priority_of(ticket["labels"]), now)
    ]
    print(json.dumps(ready))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
