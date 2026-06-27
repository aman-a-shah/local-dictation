"""Tests for the post-processing polish layer.

Covers (a) the formatting wins, (b) — most importantly — that ordinary prose is
left untouched (no false positives), and (c) that it's fast enough to be
invisible in the dictation pipeline.

The trigger is intentionally strict: a list is only produced when the speaker
explicitly signals one (an announcement cue, or a run of >=3 sequential markers).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dictate.polish import polish  # noqa: E402


# --- announcement cues ------------------------------------------------------
def test_colon_list():
    out = polish("Shopping list: milk, eggs, bread")
    assert out == "Shopping list:\n1. milk\n2. eggs\n3. bread", repr(out)


def test_grocery_colon_with_and():
    out = polish("My grocery list: milk, cheese, and bananas")
    assert out == "My grocery list:\n1. milk\n2. cheese\n3. bananas", repr(out)


def test_as_follows_without_colon():
    out = polish("The steps are as follows wake up, eat, leave")
    assert out == "The steps are as follows:\n1. wake up\n2. eat\n3. leave", repr(out)


def test_the_following():
    out = polish("Buy the following: milk, eggs, bread")
    assert out == "Buy the following:\n1. milk\n2. eggs\n3. bread", repr(out)


def test_enumerative_verb():
    out = polish("The agenda includes intros, the demo, and Q and A")
    assert out == "The agenda:\n1. intros\n2. the demo\n3. Q and A", repr(out)


def test_trailing_sentence_peeled_off():
    out = polish("My grocery list: milk, cheese, and bananas. Also grab bread.")
    assert out == (
        "My grocery list:\n1. milk\n2. cheese\n3. bananas\n\nAlso grab bread."
    ), repr(out)


# --- explicit enumeration ---------------------------------------------------
def test_cardinals():
    out = polish("One, wake up. Two, eat breakfast. Three, go to work.")
    assert out == "1. wake up\n2. eat breakfast\n3. go to work", repr(out)


def test_cardinals_with_lead_in():
    out = polish("Here's the plan. One, scope it. Two, build it. Three, ship it.")
    assert out == "Here's the plan:\n1. scope it\n2. build it\n3. ship it", repr(out)


def test_ordinals():
    out = polish("First, wake up. Second, eat breakfast. Third, go to work.")
    assert out == "1. wake up\n2. eat breakfast\n3. go to work", repr(out)


def test_ordinals_with_header():
    out = polish("My morning routine. First wake up, then second drink coffee, then third leave.")
    # header kept, ordinals enumerated
    assert out.startswith("My morning routine:\n1. wake up"), repr(out)


def test_bullet_style():
    from dictate import config

    object.__setattr__(config.CONFIG, "list_style", "bullet")
    try:
        out = polish("Shopping list: milk, eggs, bread")
        assert out == "Shopping list:\n- milk\n- eggs\n- bread", repr(out)
    finally:
        object.__setattr__(config.CONFIG, "list_style", "numbered")


# --- the list has to STOP when narration resumes ----------------------------
def test_stops_at_sentence_boundary():
    out = polish("Shopping list: milk, eggs, bread. Then I drove to the gym and worked out.")
    assert out == (
        "Shopping list:\n1. milk\n2. eggs\n3. bread\n\n"
        "Then I drove to the gym and worked out."
    ), repr(out)


def test_stops_when_narration_spans_commas():
    out = polish(
        "My grocery list: milk, eggs, bread, and then I went to the store, "
        "bought a soda, and drove home."
    )
    assert out == (
        "My grocery list:\n1. milk\n2. eggs\n3. bread\n\n"
        "and then I went to the store, bought a soda, and drove home."
    ), repr(out)


def test_enumeration_stops_at_narration():
    out = polish(
        "One, finish the report. Two, email the client. Three, book the flight. "
        "After that I took a long break and went home."
    )
    assert out == (
        "1. finish the report\n2. email the client\n3. book the flight\n\n"
        "After that I took a long break and went home."
    ), repr(out)


def test_enumeration_stops_unpunctuated():
    out = polish(
        "one finish the report, two email the client, three book the flight "
        "and then I went home and relaxed"
    )
    assert out == (
        "1. finish the report\n2. email the client\n3. book the flight\n\n"
        "and then I went home and relaxed"
    ), repr(out)


def test_closer_is_dropped():
    out = polish("Shopping list: milk, eggs, bread, that's the list.")
    assert out == "Shopping list:\n1. milk\n2. eggs\n3. bread", repr(out)


def test_closer_after_sentence_boundary_is_dropped():
    out = polish("Here are my priorities. One, sleep. Two, eat. Three, code. That is all.")
    assert out == "Here are my priorities:\n1. sleep\n2. eat\n3. code", repr(out)


def test_imperative_chain_not_split():
    # "and then add the flour" has no subject pronoun — it's a step, not narration.
    out = polish("Recipe steps: crack the eggs, whisk them and then add the flour, bake")
    assert out == (
        "Recipe steps:\n1. crack the eggs\n2. whisk them and then add the flour\n3. bake"
    ), repr(out)


# --- no false positives -----------------------------------------------------
NEGATIVES = [
    "I went to the store and bought milk, cheese, and bread.",
    "Can you hear me?",
    "Let's meet at noon tomorrow.",
    "I came first and you came second.",
    "The list is short.",
    "She said the meeting is at three.",
    "Hello, how are you doing today?",
    # bare "is"/"are" + list noun is NO LONGER a cue — must stay prose.
    "My grocery list is milk, cheese, and bananas",
    "The reasons are obvious, clear, and simple.",
    "These things are good, bad, and ugly.",
    # only two markers — below the three-marker bar.
    "First, wake up. Second, eat breakfast.",
    "One thing I want, two coffees, please.",
    # a run that doesn't start at the first marker.
    "I'll give you three reasons. Second is cost, third is time.",
]


def test_no_false_positives():
    for s in NEGATIVES:
        assert polish(s) == s, f"polish changed a non-list: {s!r} -> {polish(s)!r}"


def test_empty_and_whitespace():
    assert polish("") == ""
    assert polish("   ") == ""


def test_latency_is_negligible():
    sample = "My grocery list: milk, cheese, eggs, bread, butter, and apples"
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
