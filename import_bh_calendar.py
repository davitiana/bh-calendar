#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
from collections import defaultdict
from datetime import date
import pymupdf

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
YEAR = 2026
MONTH = 6


def get_column_boundaries(words):
    """Return list of (x_left, x_right, day_name) for each day column."""
    day_x = {w[4]: w[0] for w in words if w[4] in DAYS}
    sorted_days = sorted(day_x.items(), key=lambda d: d[1])
    boundaries = []
    for i, (day_name, x) in enumerate(sorted_days):
        left = 0 if i == 0 else (sorted_days[i - 1][1] + x) / 2
        right = float("inf") if i == len(sorted_days) - 1 else (x + sorted_days[i + 1][1]) / 2
        boundaries.append((left, right, day_name))
    return boundaries


def classify_column(x, boundaries):
    for left, right, day_name in boundaries:
        if left <= x < right:
            return day_name
    return None


def find_date_anchors(words, boundaries):
    """Return {date_num: {day, x, y}} using word-level positions."""
    anchors = {}
    for w in words:
        token = w[4].strip()
        if re.fullmatch(r"\d{1,2}", token):
            num = int(token)
            if 1 <= num <= 31:
                day = classify_column(w[0], boundaries)
                if day and num not in anchors:
                    anchors[num] = {"day": day, "x": w[0], "y": w[1]}
    return anchors


def is_date_only_block(text):
    """True if every non-empty line in the block is a plain 1-2 digit number."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return lines and all(re.fullmatch(r"\d{1,2}", ln) for ln in lines)


def is_skip_block(text):
    """True for title/header blocks that are not calendar events."""
    combined = text.strip()
    return (
        any(day in combined for day in DAYS)
        or "Bright Horizons" in combined
        or "June 2026" in combined
    )


def parse_block_text(raw):
    """Return (starts_new_event, cleaned_text) for an event block."""
    starts_new_event = raw.lstrip(" ").startswith("\n")
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    return starts_new_event, " ".join(lines)


def parse_calendar(pdf_path):
    doc = pymupdf.open(pdf_path)
    page = doc.load_page(0)

    words = page.get_text("words")  # (x0,y0,x1,y1,text,block_no,line_no,word_no)
    boundaries = get_column_boundaries(words)
    date_anchors = find_date_anchors(words, boundaries)

    # Collect event block fragments per date, preserving order and new-event markers
    # Structure: {date_num: [(y0, starts_new_event, text_fragment)]}
    raw_events = defaultdict(list)

    for block in page.get_text("blocks"):
        x0, y0, x1, y1, raw_text, _block_no, block_type = block
        if block_type != 0:  # skip image blocks
            continue
        if is_date_only_block(raw_text) or is_skip_block(raw_text):
            continue

        starts_new, text = parse_block_text(raw_text)
        if not text:
            continue

        # Classify by left edge of block (avoids word-level column overflow)
        day = classify_column(x0, boundaries)
        if day is None:
            continue

        # Find the nearest date anchor above this block in the same column
        best_date, best_y = None, -1
        for dn, anchor in date_anchors.items():
            if anchor["day"] == day and anchor["y"] <= y0:
                if anchor["y"] > best_y:
                    best_y = anchor["y"]
                    best_date = dn

        if best_date is not None:
            raw_events[best_date].append((y0, starts_new, text))

    # Assemble final event strings per date
    # Rule: first block for a date → new event; subsequent blocks start a new event
    # only if the block had a leading newline in the PDF (paragraph break).
    calendar = []
    for dn in sorted(date_anchors):
        anchor = date_anchors[dn]
        fragments = sorted(raw_events.get(dn, []), key=lambda f: f[0])

        events = []
        current_parts = []
        for i, (_, starts_new, text) in enumerate(fragments):
            if i > 0 and starts_new:
                if current_parts:
                    events.append(" ".join(current_parts))
                current_parts = [text]
            else:
                current_parts.append(text)
        if current_parts:
            events.append(" ".join(current_parts))

        calendar.append({
            "date": date(YEAR, MONTH, dn).isoformat(),
            "day_of_week": anchor["day"],
            "events": events,
        })

    return calendar


def main():
    calendar = parse_calendar("JuneCalendar.pdf")

    print("=== Bright Horizons at San Carlos — June 2026 ===\n")
    for entry in calendar:
        if entry["events"]:
            for i, event in enumerate(entry["events"]):
                prefix = f"{entry['date']} {entry['day_of_week']:9s}" if i == 0 else " " * 20
                print(f"{prefix}  {event}")
        else:
            print(f"{entry['date']} {entry['day_of_week']:9s}  (no events)")

    with open("june_calendar.json", "w") as f:
        json.dump(calendar, f, indent=2)
    print("\nSaved to june_calendar.json")


if __name__ == "__main__":
    main()
