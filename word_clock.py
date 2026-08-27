#!/usr/bin/env python3
"""
Mechanical word clock — split-flap style with exact minutes.

Each category is a roll of alternative words. Every minute is expressed
exactly using separate rolls for tens, units, and special words
(QUARTER, HALF).  The flaps flip mechanically as the time changes.

Layout (left → right):

  [TICK|TOCK]  IT  IS  [QUARTER|HALF]  [TWENTY]
  [ONE..TWELVE | THIR/FOUR/FIF/…]  [TEEN]
  [MINUTE|MINUTES]  [PAST|TO]  [hour]  [O'CLOCK]

Teens are split across two flaps, e.g. 13 → THIR + TEEN, 18 → EIGH + TEEN.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Word rolls (categories)
# ---------------------------------------------------------------------------

@dataclass
class WordRoll:
    """One mechanical flap / roll for a semantic category."""

    name: str
    words: list[str]
    current: str = ""
    blank: str = ""

    def __post_init__(self) -> None:
        if self.blank not in self.words:
            self.words = [self.blank] + list(self.words)
        if not self.current:
            self.current = self.blank

    def set(self, word: str) -> bool:
        if word not in self.words:
            raise ValueError(f"roll '{self.name}': unknown word {word!r}")
        changed = word != self.current
        self.current = word
        return changed

    def deactivate(self) -> bool:
        return self.set(self.blank)

    @property
    def active(self) -> bool:
        return self.current != self.blank

    def width(self) -> int:
        return max(len(w) for w in self.words) if self.words else 0


# ---------------------------------------------------------------------------
# Roll definitions — one roll per word-category on the mechanical display
# ---------------------------------------------------------------------------

def build_rolls() -> dict[str, WordRoll]:
    B = ""
    return {
        # -- second pendulum --
        "seconds": WordRoll(name="seconds", words=["TICK", "TOCK"], blank=B),

        # -- fixed sentence opener --
        "it": WordRoll(name="it", words=["IT"], blank=B, current="IT"),
        "is": WordRoll(name="is", words=["IS"], blank=B, current="IS"),

        # -- special minute names (replace the numeric rolls) --
        "special": WordRoll(
            name="special",
            words=["QUARTER", "HALF"],
            blank=B,
        ),

        # -- tens digit of the minute number --
        "tens": WordRoll(
            name="tens",
            words=["TWENTY"],
            blank=B,
        ),

        # -- units / stems (1–12 full words; irregular teen stems) --
        # FOUR/SIX/SEVEN/NINE do double duty: alone = 4/6/7/9, + TEEN = 14/16/17/19
        "units": WordRoll(
            name="units",
            words=[
                "ONE", "TWO", "THREE", "FOUR", "FIVE",
                "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
                "ELEVEN", "TWELVE",
                "THIR", "FIF", "EIGH",  # irregular 13/15/18 stems
            ],
            blank=B,
        ),

        # -- TEEN suffix flap (13–19) --
        "teen": WordRoll(
            name="teen",
            words=["TEEN"],
            blank=B,
        ),

        # -- MINUTE / MINUTES --
        "min_word": WordRoll(
            name="min_word",
            words=["MINUTE", "MINUTES"],
            blank=B,
        ),

        # -- relation to the hour --
        "relation": WordRoll(
            name="relation",
            words=["PAST", "TO"],
            blank=B,
        ),

        # -- the hour --
        "hour": WordRoll(
            name="hour",
            words=[
                "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX",
                "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN", "TWELVE",
            ],
            blank=B,
        ),

        # -- O'CLOCK (only at the exact hour) --
        "oclock": WordRoll(
            name="oclock",
            words=["O'CLOCK"],
            blank=B,
        ),
    }


HOUR_WORDS = [
    "TWELVE", "ONE", "TWO", "THREE", "FOUR", "FIVE",
    "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN",
]

# 1–12 as full words on the units flap
UNIT_WORDS = [
    "", "ONE", "TWO", "THREE", "FOUR", "FIVE",
    "SIX", "SEVEN", "EIGHT", "NINE", "TEN",
    "ELEVEN", "TWELVE",
]

# 13–19: stem on units + TEEN flap  →  THIR TEEN, FOUR TEEN, …
TEEN_STEMS = {
    13: "THIR",
    14: "FOUR",
    15: "FIF",
    16: "SIX",
    17: "SEVEN",
    18: "EIGH",
    19: "NINE",
}


# ---------------------------------------------------------------------------
# Time → flap state
# ---------------------------------------------------------------------------

DISPLAY_ORDER = [
    "seconds", "it", "is",
    "special", "tens", "units", "teen", "min_word",
    "relation", "hour", "oclock",
]


@dataclass
class FlapState:
    """Desired word per roll (blank string = roll idle)."""
    seconds: str = ""
    it: str = "IT"
    is_word: str = "IS"
    special: str = ""
    tens: str = ""
    units: str = ""
    teen: str = ""
    min_word: str = ""
    relation: str = ""
    hour: str = ""
    oclock: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "seconds": self.seconds,
            "it": self.it,
            "is": self.is_word,
            "special": self.special,
            "tens": self.tens,
            "units": self.units,
            "teen": self.teen,
            "min_word": self.min_word,
            "relation": self.relation,
            "hour": self.hour,
            "oclock": self.oclock,
        }

    def sentence(self) -> str:
        # Join stem+TEEN without a space so "THIR"+"TEEN" reads THIRTEEN-ish,
        # while still being two separate mechanical flaps on the board.
        parts: list[str] = [self.seconds, self.it, self.is_word, self.special, self.tens]
        if self.units and self.teen:
            parts.append(self.units + self.teen)  # THIRTEEN, FOURTEEN, …
        else:
            if self.units:
                parts.append(self.units)
            if self.teen:
                parts.append(self.teen)
        parts.extend([self.min_word, self.relation, self.hour, self.oclock])
        return " ".join(p for p in parts if p)


def hour_word(h: int) -> str:
    return HOUR_WORDS[h % 12]


def set_minute_words(state: FlapState, n: int) -> None:
    """
    Set special / tens / units / teen / min_word rolls for minute count n (1..29).
    """
    if n == 15:
        # Prefer the classic special word; numeric form would be FIF + TEEN.
        state.special = "QUARTER"
        return
    # n == 30 handled outside (HALF PAST)

    if n == 1:
        state.units = "ONE"
        state.min_word = "MINUTE"
    elif n <= 12:
        state.units = UNIT_WORDS[n]
        state.min_word = "MINUTES"
    elif n <= 19:
        state.units = TEEN_STEMS[n]
        state.teen = "TEEN"
        state.min_word = "MINUTES"
    elif n == 20:
        state.tens = "TWENTY"
        state.min_word = "MINUTES"
    else:  # 21..29
        state.tens = "TWENTY"
        state.units = UNIT_WORDS[n - 20]
        state.min_word = "MINUTES"


def resolve_time(dt: datetime) -> FlapState:
    """
    Map a datetime to exact flap words.

    minute 0       → H O'CLOCK
    minute 1–29    → <words> PAST H         (QUARTER replaces numeric at 15)
    minute 30      → HALF PAST H
    minute 31–59   → <60-m words> TO H+1    (QUARTER replaces numeric at 45)
    """
    h = dt.hour
    m = dt.minute
    s = dt.second

    state = FlapState()
    state.seconds = "TICK" if s % 2 == 0 else "TOCK"

    if m == 0:
        state.hour = hour_word(h)
        state.oclock = "O'CLOCK"
    elif m == 30:
        state.special = "HALF"
        state.relation = "PAST"
        state.hour = hour_word(h)
    elif m < 30:
        set_minute_words(state, m)
        state.relation = "PAST"
        state.hour = hour_word(h)
    else:  # m > 30
        remaining = 60 - m
        set_minute_words(state, remaining)
        state.relation = "TO"
        state.hour = hour_word(h + 1)

    return state


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

@dataclass
class WordClock:
    rolls: dict[str, WordRoll] = field(default_factory=build_rolls)
    last_sentence: str = ""
    flip_count: int = 0

    def apply(self, state: FlapState) -> list[str]:
        flipped: list[str] = []
        for name, word in state.as_dict().items():
            if self.rolls[name].set(word):
                flipped.append(name)
        if flipped:
            self.flip_count += len(flipped)
            self.last_sentence = state.sentence()
        return flipped

    def sync_now(self, dt: Optional[datetime] = None) -> list[str]:
        return self.apply(resolve_time(dt or datetime.now()))

    # -- rendering ----------------------------------------------------------

    def _cell(self, text: str, width: int, lit: bool) -> list[str]:
        pad = text.center(width)
        if lit:
            top = "┌" + "─" * (width + 2) + "┐"
            mid = "│ " + pad + " │"
            bot = "└" + "─" * (width + 2) + "┘"
        else:
            top = "┌" + "·" * (width + 2) + "┐"
            mid = "│ " + (" " * width) + " │"
            bot = "└" + "·" * (width + 2) + "┘"
        return [top, mid, bot]

    def render_flaps(self) -> str:
        cells: list[list[str]] = []
        for name in DISPLAY_ORDER:
            roll = self.rolls[name]
            w = max(roll.width(), 4)
            cells.append(self._cell(roll.current, w, roll.active))

        lines = []
        for row in range(3):
            lines.append("  ".join(cell[row] for cell in cells))
        return "\n".join(lines)

    def render_labels(self) -> str:
        labels = []
        for name in DISPLAY_ORDER:
            roll = self.rolls[name]
            w = max(roll.width(), 4) + 4
            labels.append(name.upper().center(w))
        return "  ".join(labels)

    def render_roll_inventory(self) -> str:
        lines = ["Word rolls (category → alternatives):", ""]
        for name in DISPLAY_ORDER:
            roll = self.rolls[name]
            marker = []
            for w in roll.words:
                label = w if w else "·"
                if w == roll.current:
                    marker.append(f"[{label}]")
                else:
                    marker.append(label)
            lines.append(f"  {name:10s}  " + " | ".join(marker))
        return "\n".join(lines)

    def render_frame(self, dt: datetime, flipped: Iterable[str] = ()) -> str:
        flipped_set = set(flipped)
        flip_note = (
            "flipped: " + ", ".join(sorted(flipped_set))
            if flipped_set
            else "— steady —"
        )
        digital = dt.strftime("%H:%M:%S")
        sentence = self.last_sentence or resolve_time(dt).sentence()

        parts = [
            "═" * 100,
            f"  MECHANICAL WORD CLOCK        wall {digital}        {flip_note}",
            "═" * 100,
            "",
            self.render_labels(),
            self.render_flaps(),
            "",
            f"  » {sentence}",
            "",
            self.render_roll_inventory(),
            "",
            f"  total flap moves: {self.flip_count}    Ctrl-C to stop",
            "═" * 100,
        ]
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Animation helpers
# ---------------------------------------------------------------------------

def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def animate_flip(clock: WordClock, dt: datetime, flipped: list[str]) -> None:
    if not flipped or not sys.stdout.isatty():
        return
    saved = {name: clock.rolls[name].current for name in flipped}
    for name in flipped:
        clock.rolls[name].current = clock.rolls[name].blank
    clear_screen()
    sys.stdout.write(clock.render_frame(dt, flipped) + "\n")
    sys.stdout.flush()
    time.sleep(0.08)
    for name, word in saved.items():
        clock.rolls[name].current = word


# ---------------------------------------------------------------------------
# Main loops
# ---------------------------------------------------------------------------

def run_live(once: bool = False, demo: bool = False) -> None:
    clock = WordClock()
    now = datetime.now()
    flipped = clock.sync_now(now)

    if demo:
        run_demo(clock)
        return

    try:
        while True:
            now = datetime.now()
            flipped = clock.sync_now(now)
            if flipped:
                animate_flip(clock, now, flipped)
            if sys.stdout.isatty():
                clear_screen()
            sys.stdout.write(clock.render_frame(now, flipped) + "\n")
            sys.stdout.flush()
            if once:
                break
            delay = 1.0 - (time.time() % 1.0)
            time.sleep(max(0.05, delay))
    except KeyboardInterrupt:
        sys.stdout.write("\nStopped.\n")


def run_demo(clock: WordClock) -> None:
    base = datetime.now().replace(minute=0, second=0, microsecond=0)
    print("Demo: scrubbing 0..59 minutes\n")
    for minute in range(60):
        for second in (0, 1):
            dt = base.replace(minute=minute, second=second)
            flipped = clock.sync_now(dt)
            if sys.stdout.isatty():
                animate_flip(clock, dt, flipped)
                clear_screen()
            sys.stdout.write(clock.render_frame(dt, flipped) + "\n")
            sys.stdout.flush()
            time.sleep(0.12 if second == 0 else 0.08)
    print("\nDemo finished.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mechanical English word clock (split-flap rolls) with exact minutes."
    )
    parser.add_argument("--once", action="store_true",
                        help="Print one frame and exit.")
    parser.add_argument("--demo", action="store_true",
                        help="Animate through a full hour.")
    parser.add_argument("--at", metavar="HH:MM[:SS]",
                        help="Show flaps for a specific time (implies --once).")
    args = parser.parse_args()

    if args.at:
        parts = args.at.split(":")
        if len(parts) not in (2, 3):
            parser.error("--at expects HH:MM or HH:MM:SS")
        hh, mm = int(parts[0]), int(parts[1])
        ss = int(parts[2]) if len(parts) == 3 else 0
        dt = datetime.now().replace(hour=hh, minute=mm, second=ss, microsecond=0)
        clock = WordClock()
        flipped = clock.sync_now(dt)
        print(clock.render_frame(dt, flipped))
        return

    if not sys.stdout.isatty() and not args.once and not args.demo:
        args.once = True

    run_live(once=args.once, demo=args.demo)


if __name__ == "__main__":
    main()
