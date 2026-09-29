"""Deterministic validation for the gym workflow (no LLM involved).

Nothing reaches human approval, let alone publication, without passing these rules.
Each violation names which agent should fix it, so the graph can route a revision.

Severity policy (the verdict follows from it):
  reject - retrying cannot help: an unusable request website, or no usable data at all.
  revise - the agent can fix its output; it is sent back (bounded by the graph), and a
           run that is still failing after the retries ends in a recorded safe failure.

Evidence URL policy: a source_url only counts as support when it (1) is a well-formed public
https URL, (2) is on the allow-list (the gym's own site plus GYM_URL_ALLOWLIST), and (3) is a
page the tools actually retrieved in this run. Claims backed only by other URLs are unsupported.
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
from url_policy import check_url, is_allowed_host, normalise_host, url_key

CONFIDENCE_THRESHOLD = float(os.getenv("AGENT_CONFIDENCE_THRESHOLD", "0.6"))
NO_DATA_CONFIDENCE = 0.2
WORKOUT_COUNT = 4
BEGINNER_MAX_MINUTES = 60
MAX_ITEMS_PER_LIST = 40

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

    def bad(code: str, field: str | None, message: str, severity: str = "revise") -> None:
        out.append(
            Violation(code=code, field=field, message=message, target="gym_analysis", severity=severity)
        )

    # ── URL allow-list ──────────────────────────────────────────────────
    own_host = _own_host(gym.website)
    retrieved = {url_key(u) for u in inp.retrieved_urls}
    trusted: list = []  # evidence whose citation passed every URL rule
    seen: set[tuple[str, str | None, str]] = set()

    def flag_url(code: str, field: str, key: str, message: str) -> None:
        if (code, field, key) not in seen:  # one violation per distinct problem, not per snippet
            seen.add((code, field, key))
            bad(code, field, message)

    for e in facts.evidence:
        url = e.source_url
        if not url:
            flag_url("EVIDENCE_URL_MISSING", e.field, "", f"Evidence for {e.field} has no source_url; cite the page it came from.")
            continue
        reason = check_url(url, own_host)
        if reason:
            flag_url(
                "EVIDENCE_URL_INVALID", e.field, url,
                f"Evidence URL '{url[:60]}' is not acceptable ({reason}); cite a public https page you retrieved.",
            )
            continue
        host = normalise_host(url)
        if not is_allowed_host(host, own_host):
            flag_url(
                "EVIDENCE_URL_NOT_ALLOWED", e.field, host,
                f"'{host}' is not an allowed source; cite the gym's own website or an allow-listed site.",
            )
            continue
        if url_key(url) not in retrieved:
            flag_url(
                "EVIDENCE_URL_NOT_RETRIEVED", e.field, url_key(url),
                f"'{url[:60]}' was not retrieved in this run; only cite pages the tools returned.",
            )
            continue
        trusted.append(e)

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
            for e in trusted
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
            e.field == field and _snippet_in_corpus(e.snippet, corpus_norm) for e in trusted
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

    if not facts.equipment and not facts.classes:
        bad(
            "NO_EQUIPMENT_OR_CLASSES",
            None,
            "No equipment or classes were found; retrieve more evidence, or the run will be rejected.",
        )

    for field in ("equipment", "classes"):
        items = getattr(facts, field)
        if len(items) > MAX_ITEMS_PER_LIST:
            bad("TOO_MANY_ITEMS", field, f"List at most {MAX_ITEMS_PER_LIST} {field}; keep the clearest ones.")
        keys = [_norm(i) for i in items]
        if len(set(keys)) != len(keys):
            bad("DUPLICATE_ITEMS", field, f"The {field} list repeats items; list each once.")

    return out


def _own_host(website: str | None) -> str | None:
    """The gym's own host, or None when the request website is absent or unusable."""
    if not website or check_url(website, normalise_host(website)):
        return None
    return normalise_host(website)


def _request_violations(inp: ValidatorInput) -> list[Violation]:
    """The request itself can be the problem; retrying the agents cannot fix that."""
    website = inp.gym.website
    if website and check_url(website, normalise_host(website)):
        return [
            Violation(
                code="REQUEST_WEBSITE_INVALID",
                field="website",
                message="The gym website is not a public http(s) address and was not used.",
                target="gym_analysis",
                severity="reject",
            )
        ]
    return []


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
    """Run every deterministic rule; the verdict follows from the violations' severities."""
    facts = inp.facts
    violations = _request_violations(inp)
    if facts.confidence < NO_DATA_CONFIDENCE and not facts.equipment and not facts.classes:
        violations.append(
            Violation(
                code="NO_USABLE_DATA",
                message="No equipment, classes or trustworthy evidence could be found.",
                target="gym_analysis",
                severity="reject",
            )
        )
    else:
        violations += _facts_violations(inp) + _recommendation_violations(inp)

    if any(v.severity == "reject" for v in violations):
        verdict = "reject"
    elif violations:
        verdict = "revise"
    else:
        verdict = "pass"
    return Verdict(verdict=verdict, violations=violations)
