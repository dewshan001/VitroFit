"""Deterministic validation for the gym workflow (no LLM involved).

Nothing reaches human approval, let alone publication, without passing these rules.
Each violation names which agent should fix it, so the graph can route a revision.
"""

import os
import re

from contracts import (
    GymFacts,
    Recommendations,
    ValidatorInput,
    Verdict,
    Violation,
)
from tools import DIFFICULTIES, MAX_WORKOUT_MINUTES, MIN_WORKOUT_MINUTES, WORKOUT_CATEGORIES

CONFIDENCE_THRESHOLD = float(os.getenv("AGENT_CONFIDENCE_THRESHOLD", "0.6"))
NO_DATA_CONFIDENCE = 0.2
WORKOUT_COUNT = 4
BEGINNER_MAX_MINUTES = 60

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_UNSAFE_RE = re.compile(
    r"\b(cure[sd]?|treat(s|ed|ment)?|diagnos\w*|prescri\w+|medication|steroids?|"
    r"guarantee[sd]?|miracle|pass out|collapse|vomit|no pain,? no gain)\b",
    re.IGNORECASE,
)
_BEGINNER_INTENSE_RE = re.compile(
    r"\b(max effort|one[- ]rep max|1rm|all[- ]out|to failure|to exhaustion)\b", re.IGNORECASE
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text or "")


def _item_key(text: str) -> str:
    key = _norm(text)
    return key[:-1] if key.endswith("s") and len(key) > 3 else key


def _items_match(a: str, b: str) -> bool:
    ka, kb = _item_key(a), _item_key(b)
    return bool(ka and kb and (ka == kb or ka in kb or kb in ka))


def _snippet_in_corpus(snippet: str, corpus_norm: str) -> bool:
    return _norm(snippet) in corpus_norm


def _value_in_snippet(field: str, value: str, snippet: str) -> bool:
    if field == "phone":
        return bool(_digits(value)) and _digits(value) in _digits(snippet)
    return _norm(value) in _norm(snippet)


def _facts_violations(inp: ValidatorInput) -> list[Violation]:
    facts: GymFacts = inp.facts
    gym = inp.gym
    out: list[Violation] = []
    corpus_norm = _norm(" ".join(inp.corpus))

    def bad(code: str, field: str | None, message: str) -> None:
        out.append(Violation(code=code, field=field, message=message, target="gym_analysis"))

    if facts.confidence < CONFIDENCE_THRESHOLD:
        bad(
            "LOW_CONFIDENCE",
            None,
            f"Confidence {facts.confidence:.2f} is below {CONFIDENCE_THRESHOLD:.2f}; "
            "gather stronger evidence from the sources.",
        )

    known = {
        "phone": gym.known_phone,
        "email": gym.known_email,
        "opening_hours": gym.known_hours,
    }
    for field in ("phone", "email", "opening_hours"):
        value = getattr(facts, field)
        if not value:
            continue
        if known[field] and _norm(value) == _norm(known[field]):
            continue  # matches the trusted map-provider value
        if field == "email" and not _EMAIL_RE.match(value):
            bad("INVALID_FORMAT", field, "Email address is not well formed.")
            continue
        if field == "phone" and not 7 <= len(_digits(value)) <= 15:
            bad("INVALID_FORMAT", field, "Phone number must have 7-15 digits.")
            continue
        supported = any(
            e.field == field
            and _value_in_snippet(field, value, e.snippet)
            and _snippet_in_corpus(e.snippet, corpus_norm)
            for e in facts.evidence
        )
        if not supported:
            bad(
                "UNSUPPORTED_CONTACT",
                field,
                f"{field} is not backed by an evidence snippet found in the retrieved text; "
                "leave it null unless it is written in a source.",
            )

    for field in ("equipment", "classes"):
        if getattr(facts, field) and not any(
            e.field == field and _snippet_in_corpus(e.snippet, corpus_norm) for e in facts.evidence
        ):
            bad(
                "UNSUPPORTED_ITEMS",
                field,
                f"No {field} evidence snippet from the retrieved text; cite where each came from.",
            )

    for item in facts.equipment + facts.classes:
        if len(item) > 80 or _UNSAFE_RE.search(item):
            bad("INVALID_ITEM", None, f"Item '{item[:40]}' is too long or contains unsafe wording.")
            break

    return out


def _recommendation_violations(inp: ValidatorInput) -> list[Violation]:
    recs: Recommendations = inp.recommendations
    facts = inp.facts
    out: list[Violation] = []

    def bad(code: str, field: str | None, message: str) -> None:
        out.append(
            Violation(code=code, field=field, message=message, target="workout_recommendation")
        )

    if len(recs.workouts) != WORKOUT_COUNT:
        bad("WRONG_COUNT", "workouts", f"Provide exactly {WORKOUT_COUNT} workouts.")

    names = [_norm(w.name) for w in recs.workouts]
    if len(set(names)) != len(names):
        bad("DUPLICATE_NAME", "workouts", "Workout names must be unique.")

    available = list(facts.equipment) + list(facts.classes)
    for w in recs.workouts:
        if not MIN_WORKOUT_MINUTES <= w.duration_minutes <= MAX_WORKOUT_MINUTES:
            bad(
                "DURATION_RANGE",
                w.name,
                f"Duration must be {MIN_WORKOUT_MINUTES}-{MAX_WORKOUT_MINUTES} minutes.",
            )
        if w.category not in WORKOUT_CATEGORIES:
            bad("BAD_CATEGORY", w.name, f"Category must be one of {WORKOUT_CATEGORIES}.")
        if w.difficulty not in DIFFICULTIES:
            bad("BAD_DIFFICULTY", w.name, f"Difficulty must be one of {DIFFICULTIES}.")
        for used in w.equipment_used:
            if _norm(used) == "bodyweight":
                continue
            if not any(_items_match(used, a) for a in available):
                bad(
                    "UNKNOWN_EQUIPMENT",
                    w.name,
                    f"'{used}' is not in this gym's verified equipment/classes; "
                    "use only listed items or 'bodyweight'.",
                )
        text = f"{w.name} {w.description}"
        if _UNSAFE_RE.search(text):
            bad("UNSAFE_CONTENT", w.name, "Avoid medical claims, guarantees or dangerous advice.")
        if w.difficulty == "Beginner":
            if w.duration_minutes > BEGINNER_MAX_MINUTES:
                bad("BEGINNER_TOO_LONG", w.name, f"Beginner workouts max {BEGINNER_MAX_MINUTES} min.")
            if _BEGINNER_INTENSE_RE.search(text):
                bad("BEGINNER_TOO_INTENSE", w.name, "No max-effort/failure work for beginners.")

    if _UNSAFE_RE.search(recs.notes):
        bad("UNSAFE_CONTENT", "notes", "Notes contain medical claims or guarantees.")

    return out


def validate(inp: ValidatorInput) -> Verdict:
    """Run every deterministic rule. `reject` means no usable data; `revise` is retryable."""
    facts = inp.facts
    if facts.confidence < NO_DATA_CONFIDENCE and not facts.equipment and not facts.classes:
        return Verdict(
            verdict="reject",
            violations=[
                Violation(
                    code="NO_USABLE_DATA",
                    message="No equipment, classes or trustworthy evidence could be found.",
                    target="gym_analysis",
                )
            ],
        )
    violations = _facts_violations(inp) + _recommendation_violations(inp)
    return Verdict(verdict="revise" if violations else "pass", violations=violations)
