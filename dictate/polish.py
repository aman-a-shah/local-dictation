"""Fast, deterministic post-processing of transcripts.

This is pure string/regex work — microseconds on a sentence-length string, with
no model load, network, or file I/O — so it adds **no perceptible latency** to
dictation. (A latency budget is the whole reason this is rule-based rather than a
second LLM pass.)

Headline feature: turn a *clearly announced* spoken enumeration into a list, e.g.

    "my grocery list: milk, cheese, and bananas"
        ->  my grocery list:
            1. milk
            2. cheese
            3. bananas

The bar for triggering is deliberately high — false positives (turning ordinary
prose into a list) are far worse than the occasional missed list. A list is only
produced when the speaker *explicitly signals* one, via either:

1. An **announcement cue** joined to comma/"and"-separated items:
     - a list noun before a colon ............... "shopping list: a, b, c"
     - "as follows" / "the following" ........... "the steps are as follows: a, b, c"
     - a list noun + "includes"/"consists of" ... "the agenda includes a, b, c"
   Note: a bare "is"/"are" is NOT a cue ("the reasons are clear, simple, true"
   must stay prose), so it is intentionally excluded.

2. An **explicit enumeration**: a run of at least three sequential markers —
   "one … two … three …" or "first … second … third …" — where each marker
   begins a clause and the run starts at the first marker.

A list also has to *end* somewhere: speech usually continues past it ("…milk,
eggs, bread, and then I drove home"). We stop the list at the first sign that
narration has resumed — a sentence boundary, a connector + subject pronoun, or a
"that's the list" closer — and keep the rest as a trailing paragraph (see
`_find_list_end`). Without this the items would swallow the whole tail.

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
# Explicit "a list follows" cues. A bare "is"/"are" is deliberately NOT here —
# it is the single biggest source of false positives.
_FOLLOWS = r"(?:are as follows|is as follows|as follows|the following)"
_ENUM_VERB = r"(?:includes?|including|consists? of|comprises?|comprising)"

# Sequence markers. Cardinals and ordinals are matched as separate homogeneous
# runs (we never mix "first … two … third").
_CARDINAL_WORDS = [
    "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten",
]
_ORDINAL_WORDS = [
    "first", "second", "third", "fourth", "fifth",
    "sixth", "seventh", "eighth", "ninth", "tenth",
]
# A marker begins a clause: at the very start, after sentence punctuation, or
# after "and"/"then".
_CLAUSE_START = r"(?:^|[\.,;:]\s+|\b(?:and|then)\s+)"


def _marker_re(words, suffix=""):
    alt = "|".join(words)
    return re.compile(
        rf"{_CLAUSE_START}(?P<mark>(?:{alt}){suffix})\b[\s,:\-—]*",
        re.IGNORECASE,
    )


_CARDINAL_RE = _marker_re(_CARDINAL_WORDS)
_ORDINAL_RE = _marker_re(_ORDINAL_WORDS, suffix=r"(?:ly)?")
# At least this many sequential markers before an enumeration is a list.
_MIN_ENUM = 3

_COLON_RE = re.compile(r"^(?P<head>[^:\n]{1,100}?):\s*(?P<body>.+)$", re.DOTALL)
_FOLLOWS_RE = re.compile(
    rf"^(?P<head>.*?\b{_FOLLOWS})\b[\s,:\-—]*(?P<body>.+)$",
    re.IGNORECASE | re.DOTALL,
)
_VERB_RE = re.compile(
    rf"^(?P<head>.*?\b{_LIST_NOUN}\b.*?)\s+{_ENUM_VERB}\s+(?P<body>.+)$",
    re.IGNORECASE | re.DOTALL,
)
# Trailing dangling connectors to peel off a header ("these things are" -> "these
# things"). Cue phrases like "as follows" are kept — they read fine in a header.
_HEAD_STRIP_RE = re.compile(rf"[\s:,\.\-—]*\b(?:{_ENUM_VERB}|are|is)\s*$", re.IGNORECASE)

# --- knowing where a list STOPS ---------------------------------------------
# A spoken list is followed by ordinary narration ("…milk, eggs, bread, and then
# I drove home and called a friend"). Without a stop signal the items would eat
# that whole tail. We cut at the earliest of three boundaries and keep the rest
# as a trailing prose paragraph.
_PRONOUN = r"(?:i|we|he|she|they|you|it)"
# Connectors that, when followed by a subject pronoun, mark a return to
# narration. A subject pronoun is required so imperative steps that merely chain
# actions ("preheat the oven and then add the flour") are NOT split.
_RESUME = (
    r"(?:and\s+then|then|after\s+that|afterwards?|after\s+which|"
    r"so\s+then|but\s+then|so|but|anyway|meanwhile)"
)
# Meta "that was the list" closers. Unlike narration these are dropped, not kept
# — you don't want "that's the list" typed into the document.
_CLOSER = (
    r"(?:(?:and\s+)?that(?:'s| is| was)\s+(?:it|all|everything|the\s+\w+)|"
    r"those\s+(?:are|were)\s+(?:it|all|the\s+\w+)|that\s+concludes)\b"
)

# Sentence boundary — case-sensitive so a real capital letter is required (the
# whole module otherwise runs IGNORECASE). Whisper punctuates, so this is the
# strongest and most common stop signal.
_BREAK_SENTENCE = re.compile(r"\.\s+(?=[A-Z])")
# Narration resumes: a connector + pronoun (either separator), or — at a comma,
# which already delimits an item — a bare pronoun starting a new clause. The
# connector/pronoun is looked-ahead (not consumed) so the trailer keeps it.
_BREAK_NARRATION = re.compile(
    rf"(?:[\s,]+(?={_RESUME}\s+{_PRONOUN}\b)|,\s+(?={_PRONOUN}\s+\w))",
    re.IGNORECASE,
)
_BREAK_CLOSER = re.compile(rf"[\s,]+{_CLOSER}", re.IGNORECASE)
# A trailer that is *only* a closer ("that is all.") is dropped — it may have
# been peeled off by a sentence boundary before the closer rule could fire.
_PURE_CLOSER_RE = re.compile(rf"^{_CLOSER}[\s.!]*$", re.IGNORECASE)


def _find_list_end(text: str):
    """Split text into (list_region, trailing_prose) at the first stop signal.

    The list region is everything up to the point narration resumes; the trailer
    is the prose after it (empty if the list runs to the end). A meta closer is
    consumed and dropped rather than returned as a trailer.
    """
    text = text.strip()
    cut = len(text)          # where the list region ends
    rest = len(text)         # where the trailer begins (== cut unless we drop a closer)
    for rx in (_BREAK_SENTENCE, _BREAK_NARRATION, _BREAK_CLOSER):
        m = rx.search(text)
        if m and m.start() < cut:
            cut, rest = m.start(), m.end()
    region = text[:cut].strip()
    trailer = text[rest:].lstrip(" ,.;:—-").strip() if rest < len(text) else ""
    if _PURE_CLOSER_RE.match(trailer):
        trailer = ""
    return region, trailer


def polish(text: str) -> str:
    """Return the cleaned-up transcript. Safe on empty input."""
    text = (text or "").strip()
    if not text or not CONFIG.polish:
        return text
    formatted = _format_list(text)
    return formatted if formatted is not None else text


# --- list formatting --------------------------------------------------------
def _format_list(text: str):
    # 1. Explicit enumeration ("one … two … three …") wins — it's the strongest
    #    signal and may carry its own lead-in.
    enum = _format_enumeration(text)
    if enum is not None:
        return enum

    # 2. A list noun before a colon: "shopping list: a, b, c".
    m = _COLON_RE.match(text)
    if m and re.search(rf"\b{_LIST_NOUN}\b", m.group("head"), re.IGNORECASE):
        built = _build(m.group("head"), m.group("body"))
        if built is not None:
            return built

    # 3. "as follows" / "the following" — explicit, colon optional.
    m = _FOLLOWS_RE.match(text)
    if m:
        built = _build(m.group("head"), m.group("body"))
        if built is not None:
            return built

    # 4. A list noun + an enumerative verb: "the agenda includes a, b, c".
    m = _VERB_RE.match(text)
    if m:
        built = _build(m.group("head"), m.group("body"))
        if built is not None:
            return built

    return None


def _clean_head(head: str) -> str:
    head = head.strip().rstrip(":,. ").strip()
    prev = None
    while head and head != prev:
        prev = head
        head = _HEAD_STRIP_RE.sub("", head).strip().rstrip(":,. ").strip()
    return head


def _build(head: str, body: str):
    items, trailer = _split_items(body)
    if len(items) < CONFIG.min_list_items:
        return None
    head = _clean_head(head)
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
    """Split a comma/'and' separated body into (items, trailing_prose).

    The list only runs until narration resumes — everything after that point is
    returned as a trailing paragraph rather than swallowed into items.
    """
    region, trailer = _find_list_end(body.strip())

    parts = [p.strip() for p in re.split(r"\s*,\s*", region) if p.strip()]
    if len(parts) <= 1:
        # No commas — try "a and b and c" / "a or b or c".
        parts = [p.strip() for p in re.split(r"\s+(?:and|or)\s+", region, flags=re.IGNORECASE) if p.strip()]

    items = []
    for p in parts:
        p = re.sub(r"^(?:and|or)\s+", "", p, flags=re.IGNORECASE).strip().rstrip(".").strip()
        if p:
            items.append(p)
    return items, trailer


def _format_enumeration(text: str):
    """Format "one … two … three …" / "first … second … third …" runs."""
    min_markers = max(_MIN_ENUM, CONFIG.min_list_items)
    for rx, words in ((_CARDINAL_RE, _CARDINAL_WORDS), (_ORDINAL_RE, _ORDINAL_WORDS)):
        out = _try_sequence(text, rx, words, min_markers)
        if out is not None:
            return out
    return None


def _try_sequence(text: str, rx, words, min_markers: int):
    matches = list(rx.finditer(text))
    if len(matches) < min_markers:
        return None

    seq = []
    for mt in matches:
        word = re.sub(r"ly$", "", mt.group("mark").lower())
        if word in words:
            seq.append((words.index(word), mt))

    if len(seq) < min_markers:
        return None
    ranks = [r for r, _ in seq]
    # Must be a real run: start at the first marker and include the opening
    # 0,1,2,… so a stray "second"/"third" in prose can't trip it.
    if seq[0][0] != 0 or not all(r in ranks for r in range(min_markers)):
        return None

    header = _clean_head(text[: seq[0][1].start("mark")])

    items = []
    trailer = ""
    last = len(seq) - 1
    for j, (_, mt) in enumerate(seq):
        start = mt.end()
        end = seq[j + 1][1].start() if j + 1 < len(seq) else len(text)
        item = text[start:end].strip()
        item = re.sub(r"^(?:of all)[,\s]+", "", item, flags=re.IGNORECASE)  # "first of all,"
        if j == last:
            # The final item runs to the end of the transcript, so it's where
            # trailing narration ("…book the flight and then I went home") hides.
            item, trailer = _find_list_end(item)
        item = item.strip().rstrip(".,;").strip()
        if item:
            items.append(item)

    if len(items) < min_markers:
        return None

    lines = [f"{header}:"] if header else []
    lines += _number(items)
    out = "\n".join(lines)
    if trailer:
        out += "\n\n" + trailer
    return out
