"""Tests for the post-processing polish layer.

Covers (a) the formatting wins, (b) — most importantly — that ordinary prose is
left untouched (no false positives), and (c) that it's fast enough to be
invisible in the dictation pipeline.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dictate.polish import polish  # noqa: E402


def test_grocery_list_with_and():
    out = polish("My grocery list is milk, cheese, and bananas")
    assert out == "My grocery list:\n1. milk\n2. cheese\n3. bananas", repr(out)


def test_colon_list():
    out = polish("Shopping list: milk, eggs, bread")
    assert out == "Shopping list:\n1. milk\n2. eggs\n3. bread", repr(out)


def test_todo_list():
    out = polish("my to-do list is buy milk, walk the dog, call mom")
    assert out == "my to-do list:\n1. buy milk\n2. walk the dog\n3. call mom", repr(out)


def test_trailing_sentence_peeled_off():
    out = polish("My grocery list is milk, cheese, and bananas. Also grab bread.")
    assert out == (
        "My grocery list:\n1. milk\n2. cheese\n3. bananas\n\nAlso grab bread."
    ), repr(out)


def test_ordinals():
    out = polish("First, wake up. Second, eat breakfast. Third, go to work.")
    assert out == "1. wake up\n2. eat breakfast\n3. go to work", repr(out)


def test_ordinals_with_header():
    out = polish("My morning routine. First wake up, then second drink coffee, then third leave.")
    # header kept, ordinals enumerated
    assert out.startswith("My morning routine:\n1. wake up"), repr(out)


def test_bullet_style(monkeypatch=None):
    from dictate import config

    object.__setattr__(config.CONFIG, "list_style", "bullet")
    try:
        out = polish("Shopping list: milk, eggs, bread")
        assert out == "Shopping list:\n- milk\n- eggs\n- bread", repr(out)
    finally:
        object.__setattr__(config.CONFIG, "list_style", "numbered")


# --- no false positives -----------------------------------------------------
NEGATIVES = [
    "I went to the store and bought milk, cheese, and bread.",
    "Can you hear me?",
    "Let's meet at noon tomorrow.",
    "I came first and you came second.",
    "The list is short.",
    "She said the meeting is at three.",
    "Hello, how are you doing today?",
]


def test_no_false_positives():
    for s in NEGATIVES:
        assert polish(s) == s, f"polish changed a non-list: {s!r} -> {polish(s)!r}"


def test_empty_and_whitespace():
    assert polish("") == ""
    assert polish("   ") == ""


def test_latency_is_negligible():
    sample = "My grocery list is milk, cheese, eggs, bread, butter, and apples"
    n = 2000
    t0 = time.perf_counter()
    for _ in range(n):
        polish(sample)
    per_call_us = (time.perf_counter() - t0) / n * 1e6
    print(f"\npolish: {per_call_us:0.1f} µs/call")
    # Must be trivially small vs ~1.5s transcription. 2 ms is a very loose bound.
    assert per_call_us < 2000, f"too slow: {per_call_us} µs/call"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"✓ {fn.__name__}")
    print("\nAll polish checks passed.")
