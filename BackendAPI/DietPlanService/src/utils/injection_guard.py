# DietPlanService/src/utils/injection_guard.py
"""Deterministic prompt-injection guard (no LLM, no I/O).

Untrusted text enters this service in two places: the free-text fields a user
types (`dislikes`, the refine `instruction`) and the model's own output (meal
names and portions). The guard runs at each boundary. It is a risk reducer, not
a proof - regex detection is never complete - so the controls that really keep
a plan safe are still the deterministic Safety Validator (restrictions, medical
rules, calorie bounds), the fixed calculator targets and the Trainer/Admin
approval of high-risk plans. The guard only makes an attack harder and visible.

How it works
  1. Normalise: NFKC, invisible/bidi/control characters removed, whitespace collapsed.
  2. Fold a same-length matching copy (lower-case, Cyrillic/Greek look-alikes ->
     Latin) so "ignоre" with a Cyrillic "o" is still caught.
  3. Run the signal rules. Each has a code and a weight; strong signals try to
     instruct the model, weak ones are only suspicious.
  4. A short field is blocked (the request is refused) on any strong signal or a
     high total score. Nothing is silently rewritten.

Mode (DIET_INJECTION_MODE): `enforce` (default) blocks; `monitor` only detects
and reports, so a false-positive problem can be diagnosed without refusing users.
"""
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field

from src.utils.logger import log_event

STRONG_WEIGHT = 3
WEAK_WEIGHT = 1
DEFAULT_BLOCK_SCORE = 3     # one strong signal blocks a short field
MAX_MATCHES_PER_RULE = 5    # bounds work and score on pathological input
MAX_SCAN_CHARS = 20000

_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿­᠎͏]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Look-alike letters folded to the Latin letter they imitate. One character in,
# one character out, so match offsets stay valid.
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
    plain: bool = False  # match on the lower-cased copy instead of the look-alike-folded one

    @property
    def strong(self) -> bool:
        return self.weight >= STRONG_WEIGHT


def _rx(pattern: str) -> re.Pattern:
    return re.compile(pattern, re.MULTILINE)


_GAP = r"[^.!?\n]"  # stay inside one sentence

RULES: tuple[Rule, ...] = (
    # -- strong: the text tries to instruct the model -------------------------
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
        r"(?:^|(?<=[.!?;])\s+)\s*###\s*(?:system|instruction|assistant|human|user)\b")),
    Rule("ROLE_LINE_WITH_COMMAND", STRONG_WEIGHT, _rx(
        r"(?:^|(?<=[.!?;])\s+)\s*(?:system|assistant|developer|human)\s*:\s*(?:you|ignore|from now|new|do|set|call|use|reveal|"
        r"output|respond|answer|always|never|your|please|disregard|forget)\b")),
    Rule("FENCE_BREAKOUT", STRONG_WEIGHT, _rx(
        r"</?\s*(?:untrusted[_ -]?sources?|system|instructions?|assistant|prompt)\s*/?\s*>")),
    Rule("TOOL_COERCION", STRONG_WEIGHT, _rx(
        rf"\b(?:call|invoke|run|execute)\b{_GAP}{{0,30}}?\b(?:tools?|functions?)\b|"
        r"\b(?:generate_meals|refine_meals|validate_plan|calculate_targets|assess_risk|lookup_budget)\b")),
    Rule("VERDICT_COERCION", STRONG_WEIGHT, _rx(
        r"\b(?:set|change|overwrite|replace)\s+(?:the\s+)?(?:verdict|approval|approved|risk(?:\s+level)?|validation|safety(?:\s+check)?)\s*"
        r"(?:status|result)?\s*(?:to|=|as)\b|"
        r"\b(?:mark|set|treat)\b" + _GAP + r"{0,30}?\b(?:as\s+)?(?:verified|approved|trusted|safe)\b|"
        r"\bapprove\s+(?:this|the)\s+(?:plan|run|workflow|request)\b|"
        r"\b(?:skip|disable|turn off)\b" + _GAP + r"{0,20}?\b(?:validation|validator|safety|checks?)\b")),
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
    # -- weak: suspicious on their own, only recorded --------------------------
    Rule("ROLE_PLAY", WEAK_WEIGHT, _rx(
        r"\byou are now\s+(?:a|an)\b|\b(?:act|behave|respond)\s+as\s+(?:a|an|if)\b|\bpretend\s+(?:to be|you)\b|"
        r"\bjailbreak\b|\bdeveloper mode\b|\bdo anything now\b|\bdan mode\b")),
    Rule("FROM_NOW_ON", WEAK_WEIGHT, _rx(rf"\bfrom now on\b{_GAP}{{0,40}}?\b(?:you|always|only|never)\b")),
    Rule("ENCODED_BLOB", WEAK_WEIGHT, _rx(r"[a-z0-9+/]{80,}={0,2}|[0-9a-f]{64,}")),
)

_RULES_FOLDED = tuple(r for r in RULES if not r.plain)
_RULES_PLAIN = tuple(r for r in RULES if r.plain)

# Markup or links in fields that must be plain text (meal item names, portions).
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
    return "monitor" if os.getenv("DIET_INJECTION_MODE", "enforce").strip().lower() == "monitor" else "enforce"


def block_score() -> int:
    try:
        return max(1, int(os.getenv("DIET_INJECTION_BLOCK_SCORE", DEFAULT_BLOCK_SCORE)))
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
    """A single-line, safe-to-store version of untrusted text."""
    return " ".join(_base(text).split())


def _matches(base: str) -> list[Rule]:
    plain = _lower_same_length(base)
    folded = plain.translate(_HOMOGLYPHS)
    # A payload can be split over lines ("ignore all\nprevious\ninstructions"), so rules see newlines as spaces.
    flat_folded, flat_plain = folded.replace("\n", " "), plain.replace("\n", " ")
    found: list[Rule] = []
    for rules, haystack in ((_RULES_FOLDED, flat_folded), (_RULES_PLAIN, flat_plain)):
        for rule in rules:
            for i, m in enumerate(rule.pattern.finditer(haystack)):
                if i >= MAX_MATCHES_PER_RULE:
                    break
                if m.end() > m.start():
                    found.append(rule)
    return found


def scan(text: str) -> list[Finding]:
    """Detect only. Used to judge text (model output) without changing it."""
    try:
        return [Finding(r.code, r.weight, r.strong) for r in _matches(_base(text)[:MAX_SCAN_CHARS])]
    except Exception:  # never let the guard itself break a run
        log_event("injection scan failed", level=logging.ERROR)
        return []


def guard_field(text: str | None, *, source: str = "field", limit: int = 500) -> Guarded:
    """A short user-typed field (dislikes, refine instruction): normalise, scan,
    and block on a strong signal. The returned text is the normalised text; it is
    refused (blocked, text empty) rather than silently rewritten."""
    current_mode = mode()
    try:
        base = _base(text or "")[:limit]
        findings = [Finding(r.code, r.weight, r.strong) for r in _matches(base)]
    except Exception:
        # Fail closed: if the guard cannot judge the text, the model does not get it.
        log_event("injection guard failed", level=logging.ERROR, source=source)
        return Guarded("", [Finding("GUARD_ERROR", STRONG_WEIGHT, True)], blocked=True, mode=current_mode)

    result = Guarded(base, findings, mode=current_mode)
    if findings:
        # Codes and counts only: never the text itself (it may be hostile, and log lines are trusted output).
        log_event("prompt-injection signal", level=logging.WARNING, source=source, mode=current_mode,
                  codes=",".join(result.flags), score=result.score)
        if current_mode == "enforce" and (result.strong or result.score >= block_score()):
            result.blocked = True
            result.text = ""
    return result


def escape_for_fence(text: str) -> str:
    """Make it impossible to write a tag: angle brackets become look-alikes that cannot close a fence."""
    return text.replace("<", "‹").replace(">", "›")


def has_markup_or_link(text: str) -> bool:
    return bool(_MARKUP.search(text or ""))


def has_url(text: str) -> bool:
    return bool(_URL.search(text or ""))


def looks_like_blob(text: str) -> bool:
    return bool(_BLOB.search(text or ""))
