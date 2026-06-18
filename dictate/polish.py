"""Fast, deterministic post-processing of transcripts.

This is pure string/regex work — microseconds on a sentence-length string, with
no model load, network, or file I/O — so it adds **no perceptible latency** to
dictation. (A latency budget is the whole reason this is rule-based rather than a
second LLM pass.)

Headline feature: turn a spoken enumeration into a formatted list, e.g.

    "my grocery list is milk, cheese, and bananas"
        ->  my grocery list:
            1. milk
            2. cheese
            3. bananas

Two patterns are recognised, both conservative to avoid mangling normal prose:

1. A lead-in containing a list noun ("list", "steps", "ingredients", …) joined
   to comma-separated items by ":"/"is"/"are"/"includes".
2. An ordinal enumeration ("first … second … third …") where the ordinals begin
   clauses.

Everything else is returned unchanged.
"""

from __future__ import annotations

import re

from .config import CONFIG

# Nouns that signal "what follows is a list". Kept fairly specific on purpose.
_LIST_NOUN = (
    r"(?:lists?|items?|steps?|things|reasons?|options?|points?|tasks?|to-?dos?|"
    r"groceries|grocery|ingredients?|agenda|checklist|menu|priorities|errands?|plans?)"
)
_CONNECTOR = r"(?:are as follows|is as follows|includes?|including|consists? of|are|is)"

_ORDINAL_WORDS = [
    "first", "second", "third", "fourth", "fifth",
    "sixth", "seventh", "eighth", "ninth", "tenth",
]
_ORDINAL = r"(?:%s)(?:ly)?" % "|".join(_ORDINAL_WORDS)
# An ordinal that begins a clause: at the start, or after sentence punctuation,
# or after "and"/"then".
_ORDINAL_RE = re.compile(
    rf"(?:^|[\.,;:]\s+|\b(?:and|then)\s+)(?P<ord>{_ORDINAL})\b[\s,:\-—]*",
    re.IGNORECASE,
)

_COLON_RE = re.compile(r"^(?P<head>[^:\n]{1,100}?):\s*(?P<body>.+)$", re.DOTALL)
_CONNECTOR_RE = re.compile(
    rf"^(?P<head>.*?\b{_LIST_NOUN}\b.*?)\s+{_CONNECTOR}\s+(?P<body>.+)$",
    re.IGNORECASE | re.DOTALL,
)


def polish(text: str) -> str:
    """Return the cleaned-up transcript. Safe on empty input."""
    text = (text or "").strip()
    if not text or not CONFIG.polish:
        return text
    formatted = _format_list(text)
    return formatted if formatted is not None else text


# --- list formatting --------------------------------------------------------
def _format_list(text: str):
    ordinal = _format_ordinals(text)
    if ordinal is not None:
        return ordinal

    m = _COLON_RE.match(text)
    if m and re.search(rf"\b{_LIST_NOUN}\b", m.group("head"), re.IGNORECASE):
        built = _build(m.group("head"), m.group("body"))
        if built is not None:
            return built

    m = _CONNECTOR_RE.match(text)
    if m:
        built = _build(m.group("head"), m.group("body"))
        if built is not None:
            return built

    return None


def _build(head: str, body: str):
    items, trailer = _split_items(body)
    if len(items) < CONFIG.min_list_items:
        return None
    head = head.strip().rstrip(":,. ").strip()
    lines = [f"{head}:"] if head else []
    lines += _number(items)
    out = "\n".join(lines)
    if trailer:
        out += "\n\n" + trailer
    return out


def _number(items):
    bullet = CONFIG.list_style == "bullet"
    return [f"- {it}" if bullet else f"{i}. {it}" for i, it in enumerate(items, 1)]


def _split_items(body: str):
    """Split a comma/'and' separated body into (items, trailing_sentence)."""
    body = body.strip()

    parts = [p.strip() for p in re.split(r"\s*,\s*", body) if p.strip()]
    if len(parts) <= 1:
        # No commas — try "a and b and c" / "a or b or c".
        parts = [p.strip() for p in re.split(r"\s+(?:and|or)\s+", body, flags=re.IGNORECASE) if p.strip()]

    cleaned = [re.sub(r"^(?:and|or)\s+", "", p, flags=re.IGNORECASE).strip() for p in parts]

    trailer = ""
    if cleaned:
        # A sentence after the list ("…bananas. Also grab bread.") shouldn't
        # become a list item — peel it off the final item.
        m = re.match(r"^(?P<item>.+?)\.\s+(?P<rest>[A-Z].*)$", cleaned[-1], re.DOTALL)
        if m:
            cleaned[-1] = m.group("item").strip()
            trailer = m.group("rest").strip()

    items = [c.rstrip(".").strip() for c in cleaned if c.rstrip(".").strip()]
    return items, trailer


def _format_ordinals(text: str):
    matches = list(_ORDINAL_RE.finditer(text))
    if len(matches) < 2:
        return None

    seq = []
    for mt in matches:
        word = re.sub(r"ly$", "", mt.group("ord").lower())
        if word in _ORDINAL_WORDS:
            seq.append((_ORDINAL_WORDS.index(word), mt))
    rank = [r for r, _ in seq]
    # Require at least "first" and "second" so we don't trip on a stray ordinal.
    if 0 not in rank or 1 not in rank:
        return None

    header = text[: seq[0][1].start("ord")].strip().rstrip(":,. ").strip()
    # Drop a dangling connector like "are" / "is" / "as follows" from the header.
    header = re.sub(rf"\s+{_CONNECTOR}$", "", header, flags=re.IGNORECASE).strip()

    items = []
    for j, (_, mt) in enumerate(seq):
        start = mt.end()
        end = seq[j + 1][1].start() if j + 1 < len(seq) else len(text)
        item = text[start:end].strip()
        item = re.sub(r"^(?:of all)[,\s]+", "", item, flags=re.IGNORECASE)  # "first of all,"
        item = item.strip().rstrip(".,;").strip()
        if item:
            items.append(item)

    if len(items) < 2:
        return None

    lines = [f"{header}:"] if header else []
    lines += _number(items)
    return "\n".join(lines)
