"""Deterministic prompt-injection guard (no LLM, no I/O).

Untrusted text (scraped pages, search results, OSM-supplied gym names, reviewer feedback) is
checked at every trust boundary. The guard detects, neutralises, reports, and blocks only when
the evidence is strong. It is a risk reducer, not a proof: regex detection is never complete, so
the controls that really keep the system safe are still the allow-listed tools and URLs, the
deterministic validator, the human approval step and the database constraint.

How it works
  1. Normalise a base copy: NFKC, invisible/bidi/control characters removed, whitespace collapsed.
  2. Fold a matching copy of the SAME LENGTH (lower-case, look-alike letters -> Latin), so every
     match position maps straight back onto the base text.
  3. Run the signal patterns on the folded copy. Each has a code, a weight and a strength.
  4. Strong signals: the sentence around the match is removed (windowed, so one poisoned sentence in
     a long unpunctuated page does not delete the whole page).
  5. If the total weight is high, or most of the text was removed, the whole source is BLOCKED.

Modes (GYM_INJECTION_MODE): `enforce` (default) removes and blocks; `monitor` only detects and
reports, so a false-positive problem can be diagnosed without breaking runs.
"""

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger("gym_agent")

STRONG_WEIGHT = 3
WEAK_WEIGHT = 1
DEFAULT_BLOCK_SCORE = 9          # three strong signals
BLOCK_REMOVED_FRACTION = 0.5     # ...or this much of a non-trivial text had to be removed
MIN_LEN_FOR_FRACTION = 400       # (one removed sentence is a big share of a tiny text; that is not an attack)
WINDOW_BEFORE = 100              # max chars removed before a match (stops at a sentence boundary)
WINDOW_AFTER = 140               # max chars removed after a match
MAX_MATCHES_PER_RULE = 5         # bounds work and score on pathological input

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿­᠎͏]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_BOUNDARY = re.compile(r"[.!?;\n]")

# Look-alike letters (Cyrillic/Greek) folded to the Latin letter they imitate. One character in,
# one character out: this is what keeps match offsets valid on the base text.
_HOMOGLYPHS = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "ѕ": "s",
    "һ": "h", "ԁ": "d", "к": "k", "м": "m", "т": "t", "н": "h", "в": "b", "ѵ": "v", "ɡ": "g", "ⅼ": "l",
    "ο": "o", "α": "a", "ε": "e", "ι": "i", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "κ": "k", "χ": "x",
    "ı": "i", "ǃ": "!",
})


def _lower_same_length(text: str) -> str:
    """str.lower() can change the length (e.g. dotted capital I); keep offsets valid."""
    return "".join(c.lower() if len(c.lower()) == 1 else c for c in text)


@dataclass(frozen=True)
class Rule:
    code: str
    weight: int
    pattern: re.Pattern
    plain: bool = False      # match on the lower-cased copy instead of the look-alike-folded one
    anchored: bool = False   # needs real line starts (^), so it sees newlines; all others see them as spaces

    @property
    def strong(self) -> bool:
        return self.weight >= STRONG_WEIGHT


def _rx(pattern: str, flags: int = re.MULTILINE) -> re.Pattern:
    return re.compile(pattern, flags)


_GAP = r"[^.!?\n]"   # stay inside one sentence

RULES: tuple[Rule, ...] = (
    # ── strong: the text tries to instruct the model ───────────────────
    Rule("OVERRIDE_INSTRUCTIONS", STRONG_WEIGHT, _rx(
        rf"\b(?:ignore|disregard|forget|override|bypass|discard)\b{_GAP}{{0,60}}?"
        r"\b(?:instructions?|prompts?|guidelines?|directives?|system messages?|safeguards?|safety (?:rules|filters)|"
        r"(?:the|these|those|all|any|your|my|previous|prior|above|earlier)\s+(?:\w+\s+){0,2}?(?:rules|policies|constraints|restrictions))\b|"
        rf"\b(?:ignore|disregard|forget)\b{_GAP}{{0,20}}?\b(?:everything|anything|all)\b{_GAP}{{0,20}}?"
        r"\b(?:above|before|previously|said|told|you were told)\b")),
    Rule("EXFIL_PROMPT_OR_SECRET", STRONG_WEIGHT, _rx(
        rf"\b(?:reveal|show|print|repeat|output|display|leak|disclose|share|send|write out|tell me)\b{_GAP}{{0,50}}?"
        r"\b(?:system prompt|system message|your prompt|your instructions|initial prompt|hidden prompt|"
        r"api[ _-]?keys?|secrets?|passwords?|credentials?|access tokens?|bearer tokens?|environment variables?)\b")),
    Rule("CHAT_TEMPLATE_MARKER", STRONG_WEIGHT, _rx(
        r"<\|(?:im_start|im_end|system|user|assistant|endoftext)\|>|\[/?inst\]|<<sys>>|"
        r"(?:^|(?<=[.!?;])\s+)\s*###\s*(?:system|instruction|assistant|human|user)\b"), anchored=True),
    Rule("ROLE_LINE_WITH_COMMAND", STRONG_WEIGHT, _rx(
        r"(?:^|(?<=[.!?;])\s+)\s*(?:system|assistant|developer|human)\s*:\s*(?:you|ignore|from now|new|do|set|call|use|reveal|"
        r"output|respond|answer|always|never|your|please|disregard|forget)\b"), anchored=True),
    Rule("FENCE_BREAKOUT", STRONG_WEIGHT, _rx(
        r"</?\s*(?:untrusted[_ -]?sources?|system|instructions?|assistant|prompt)\s*/?\s*>")),
    Rule("TOOL_COERCION", STRONG_WEIGHT, _rx(
        rf"\b(?:call|invoke|run|execute)\b{_GAP}{{0,30}}?\b(?:tools?|functions?)\b|"
        r"\b(?:scrape_gym_website|search_gym_info|lookup_similar_gyms|list_equipment_taxonomy)\b")),
    Rule("FIELD_COERCION", STRONG_WEIGHT, _rx(
        r"\b(?:set|change|overwrite|replace)\s+(?:the\s+)?(?:phone|email|e-mail|opening hours|confidence|source|verdict|"
        r"approval|approved|equipment|classes)\s*(?:number|address)?\s*(?:to|=|as)\b|"
        r"\b(?:mark|set|treat)\b" + _GAP + r"{0,30}?\b(?:as\s+)?(?:verified|approved|trusted)\b|"
        r"\bapprove\s+(?:this|the)\s+(?:gym|run|workflow|request)\b")),
    Rule("OUTPUT_HIJACK", STRONG_WEIGHT, _rx(
        rf"\b(?:respond|reply|answer|output|return)\b{_GAP}{{0,20}}?\b(?:only|exactly|just)\b{_GAP}{{0,30}}?\b(?:json|following|below|this)\b")),
    Rule("NEW_INSTRUCTIONS", STRONG_WEIGHT, _rx(r"\bnew\s+(?:instructions?|task|objective|rules?)\s*[:\-]")),
    Rule("EXFIL_LINK", STRONG_WEIGHT, _rx(
        r"!\[[^\]]*\]\(\s*https?://[^)\s]*[?&][^)\s]*\)|"
        r"\[[^\]]*\]\(\s*https?://[^)\s]*\?[^)\s]+\)|"
        rf"\b(?:send|post|forward|upload|exfiltrate|submit)\b{_GAP}{{0,60}}?\bhttps?://")),
    Rule("OVERRIDE_INSTRUCTIONS_NON_LATIN", STRONG_WEIGHT, _rx(
        r"игнорируй\s+(?:все\s+)?(?:предыдущие|прошлые|прежние)\s+инструкции|"
        r"забудь\s+(?:все\s+)?(?:предыдущие|прошлые)\s+инструкции|"
        r"忽略(?:之前|以上|上面|所有)(?:的)?(?:指令|指示|提示)|"
        r"以前の指示を無視"), plain=True),
    Rule("OVERRIDE_INSTRUCTIONS_OTHER_LANGUAGE", STRONG_WEIGHT, _rx(
        r"\bignora\s+(?:todas\s+)?las\s+instrucciones\s+(?:anteriores|previas)\b|"
        r"\bignorez\s+(?:toutes\s+)?les\s+instructions\s+pr[eé]c[eé]dentes\b|"
        r"\bignoriere\s+(?:alle\s+)?(?:vorherigen|obigen|bisherigen)\s+(?:anweisungen|instruktionen)\b|"
        r"\bignore\s+(?:todas\s+)?as\s+instru[cç][oõ]es\s+anteriores\b")),
    # ── weak: suspicious on their own, only recorded (they add up towards a block) ──
    Rule("ROLE_PLAY", WEAK_WEIGHT, _rx(
        r"\byou are now\s+(?:a|an)\b|\b(?:act|behave|respond)\s+as\s+(?:a|an|if)\b|\bpretend\s+(?:to be|you)\b|"
        r"\bjailbreak\b|\bdeveloper mode\b|\bdo anything now\b|\bdan mode\b")),
    Rule("FROM_NOW_ON", WEAK_WEIGHT, _rx(rf"\bfrom now on\b{_GAP}{{0,40}}?\b(?:you|always|only|never)\b")),
    Rule("ENCODED_BLOB", WEAK_WEIGHT, _rx(r"[a-z0-9+/]{80,}={0,2}|[0-9a-f]{64,}")),
)

_RULES_ANCHORED = tuple(r for r in RULES if r.anchored)
_RULES_FLAT = tuple(r for r in RULES if not r.plain and not r.anchored)
_RULES_PLAIN = tuple(r for r in RULES if r.plain)

# Markup or links in fields that must be plain text (workout names, descriptions, notes...).
_MARKUP = re.compile(r"https?://|\bwww\.|<[a-z/!][^>]*>|\[[^\]]+\]\([^)]+\)|`{3}", re.IGNORECASE)
_URL = re.compile(r"https?://|\bwww\.", re.IGNORECASE)
_BLOB = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")


@dataclass(frozen=True)
class Finding:
    code: str
    weight: int
    strong: bool


@dataclass
class Guarded:
    text: str
    findings: list[Finding] = field(default_factory=list)
    blocked: bool = False
    removed_chars: int = 0
    mode: str = "enforce"

    @property
    def flags(self) -> list[str]:
        return sorted({f.code for f in self.findings})

    @property
    def score(self) -> int:
        return sum(f.weight for f in self.findings)

    @property
    def strong(self) -> bool:
        return any(f.strong for f in self.findings)

    @property
    def flagged(self) -> bool:
        return bool(self.findings)


def mode() -> str:
    return "monitor" if os.getenv("GYM_INJECTION_MODE", "enforce").strip().lower() == "monitor" else "enforce"


def block_score() -> int:
    try:
        return max(1, int(os.getenv("GYM_INJECTION_BLOCK_SCORE", DEFAULT_BLOCK_SCORE)))
    except ValueError:
        return DEFAULT_BLOCK_SCORE


def _base(text: str) -> str:
    """NFKC, no invisible or control characters, whitespace collapsed per line."""
    text = unicodedata.normalize("NFKC", text or "")
    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub("", text)
    lines = (re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def normalise_field(text: str) -> str:
    """A single-line, safe-to-store version of untrusted text: NFKC, no invisible/control characters
    (PostgreSQL cannot store NUL at all), whitespace collapsed. Applied where requests enter the service."""
    return " ".join(_base(text).split())


def _matches(base: str) -> list[tuple[Rule, int, int]]:
    plain = _lower_same_length(base)
    folded = plain.translate(_HOMOGLYPHS)
    assert len(plain) == len(folded) == len(base)
    found: list[tuple[Rule, int, int]] = []
    # A payload can be split over lines ("ignore all\nprevious\ninstructions"), so most rules see newlines as
    # spaces (same length, offsets unchanged); only line-start rules need the real line structure.
    flat_folded, flat_plain = folded.replace("\n", " "), plain.replace("\n", " ")
    for rules, haystack in ((_RULES_ANCHORED, folded), (_RULES_FLAT, flat_folded), (_RULES_PLAIN, flat_plain)):
        for rule in rules:
            for i, m in enumerate(rule.pattern.finditer(haystack)):
                if i >= MAX_MATCHES_PER_RULE:
                    break
                if m.end() > m.start():
                    found.append((rule, m.start(), m.end()))
    return found


def _window(base: str, start: int, end: int) -> tuple[int, int]:
    """The sentence around a match, but never more than WINDOW_BEFORE/AFTER either side."""
    lo = max(0, start - WINDOW_BEFORE)
    before = list(_BOUNDARY.finditer(base, lo, start))
    if before:
        lo = before[-1].end()
    hi = min(len(base), end + WINDOW_AFTER)
    after = _BOUNDARY.search(base, end, hi)
    if after:
        hi = after.end()
    return lo, hi


def scan(text: str) -> list[Finding]:
    """Detect only. Used to judge text (request fields, model output) without changing it."""
    try:
        return [Finding(r.code, r.weight, r.strong) for r, _, _ in _matches(_base(text)[:20000])]
    except Exception:  # never let the guard itself break a run
        logger.exception("Injection scan failed")
        return []


def guard_text(text: str, *, source: str = "text", limit: int = 6000, sentences: bool = True) -> Guarded:
    """Clean untrusted text. `sentences=False` only normalises and reports (for short plain fields)."""
    current_mode = mode()
    try:
        base = _base(text)[:limit]
        matches = _matches(base)
    except Exception:
        # Fail closed: if the guard cannot judge the text, the model does not get it.
        logger.exception("Injection guard failed on %s", source)
        return Guarded("", [Finding("GUARD_ERROR", STRONG_WEIGHT, True)], blocked=True, mode=current_mode)

    findings = [Finding(r.code, r.weight, r.strong) for r, _, _ in matches]
    result = Guarded(base, findings, mode=current_mode)

    if findings:
        _log_findings(source, result)
    if current_mode == "monitor" or not sentences:
        return result

    spans = sorted(_window(base, s, e) for r, s, e in matches if r.strong)
    merged: list[list[int]] = []
    for lo, hi in spans:
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])

    cleaned, cursor = [], 0
    for lo, hi in merged:
        cleaned.append(base[cursor:lo])
        cursor = hi
    cleaned.append(base[cursor:])
    result.removed_chars = sum(hi - lo for lo, hi in merged)
    result.text = "\n".join(l for l in (re.sub(r" {2,}", " ", part).strip() for part in "".join(cleaned).split("\n")) if l)

    too_much_removed = len(base) >= MIN_LEN_FOR_FRACTION and result.removed_chars >= BLOCK_REMOVED_FRACTION * len(base)
    if result.score >= block_score() or too_much_removed:
        result.blocked = True
        result.text = ""
    return result


def guard_field(text: str | None, limit: int = 500) -> Guarded:
    """Short plain-text fields (gym name, address): normalise and report, never rewrite sentences."""
    return guard_text(text or "", source="field", limit=limit, sentences=False)


def escape_for_fence(text: str) -> str:
    """Make it impossible to write a tag: angle brackets become look-alikes that cannot close a fence."""
    return text.replace("<", "‹").replace(">", "›")


def has_markup_or_link(text: str) -> bool:
    return bool(_MARKUP.search(text or ""))


def has_url(text: str) -> bool:
    return bool(_URL.search(text or ""))


def looks_like_blob(text: str) -> bool:
    return bool(_BLOB.search(text or ""))


def _log_findings(source: str, guarded: Guarded) -> None:
    # Codes and counts only: never the text itself (it may be hostile, and log lines are trusted output).
    logger.warning(
        "prompt-injection signal source=%s mode=%s codes=%s score=%d strong=%s",
        source, guarded.mode, ",".join(guarded.flags), guarded.score, guarded.strong,
    )
