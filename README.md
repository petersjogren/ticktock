# TickTock

A mechanical English word clock. Time is spelled out on split-flap rolls — one roll per word category. As the time changes, the matching word on each roll flips into the display.

Two faces, same logic:

- **Wall plaque** — live at [petersjogren.github.io/ticktock](https://petersjogren.github.io/ticktock/) (`index.html`)
- **Terminal** — `word_clock.py`

## Word rolls

| Roll | Words | Lit when |
|------|--------|----------|
| seconds | TICK, TOCK | every second (even / odd) |
| it / is | IT, IS | always |
| special | QUARTER, HALF | :15 / :45 and :30 |
| tens | TWENTY | 20–29 minutes past, or 31–40 to |
| units | ONE…TWELVE, THIR, FIF, EIGH | exact minute (stems for teens) |
| teen | TEEN | 13–14 and 16–19 |
| min_word | MINUTE, MINUTES | singular at 1, else plural |
| relation | PAST, TO | before / after the half |
| hour | ONE…TWELVE | always |
| oclock | O'CLOCK | only at :00 |

Teens are two flaps: `FOUR` + `TEEN` → fourteen. FOUR / SIX / SEVEN / NINE sit on the units roll and do double duty (alone = 4/6/7/9, with TEEN = 14/16/17/19). THIR / FIF / EIGH are extra stems for 13 / 15 / 18. Quarter and half keep their special words instead of the numeric form.

## How minutes are spoken

| Minute | Phrase |
|--------|--------|
| 0 | IT IS *hour* O'CLOCK |
| 1 | IT IS ONE MINUTE PAST *hour* |
| 2–12 | IT IS *n* MINUTES PAST *hour* |
| 13–14, 16–19 | IT IS *stem* TEEN MINUTES PAST *hour* |
| 15 | IT IS QUARTER PAST *hour* |
| 20 | IT IS TWENTY MINUTES PAST *hour* |
| 21–29 | IT IS TWENTY *n* MINUTES PAST *hour* |
| 30 | IT IS HALF PAST *hour* |
| 31–59 | same pattern with TO *next hour* |

Examples: `14:01` → *one minute past two*; `14:18` → *eighteen minutes past two*; `14:45` → *quarter to three*; `23:59` → *one minute to twelve*.

## Wall plaque

Live: https://petersjogren.github.io/ticktock/

Or open `index.html` in a browser.

Walnut frame on a plaster wall. Split-flap modules drop like Solari cards. TICK / TOCK flips every second; the other rolls flip when the minute (or demo) changes. Idle rolls collapse so the sentence stays packed inside the rectangle.

Click the hanging ring to wind a demo hour (one minute per second). Click again for live time.

## Terminal

```bash
python3 word_clock.py              # live, updates every second
python3 word_clock.py --once       # one frame for now
python3 word_clock.py --at 14:45
python3 word_clock.py --demo       # scrub 0..59 minutes
```

No dependencies beyond Python 3.

## License

Personal project. Use freely.
