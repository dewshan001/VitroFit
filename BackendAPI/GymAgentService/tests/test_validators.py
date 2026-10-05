import pytest

from src.agent.nodes import planner
from src.models.contracts import ValidatorInput
from tests.support import SITE_TEXT, WEBSITE, golden_facts, golden_recs, gym_request, workout
from src.utils.validators import validate


def make(facts=None, recs=None, corpus=None, gym=None, retrieved=None):
    gym = gym or gym_request()
    return ValidatorInput(
        gym=gym,
        plan=planner.run(gym),
        facts=facts or golden_facts(),
        recommendations=recs or golden_recs(),
        corpus=[SITE_TEXT] if corpus is None else corpus,
        retrieved_urls=[WEBSITE] if retrieved is None else retrieved,
    )


def codes(verdict):
    return {v.code for v in verdict.violations}


def test_golden_output_passes():
    verdict = validate(make())
    assert verdict.verdict == "pass" and not verdict.violations


def test_invented_phone_is_rejected_for_revision():
    facts = golden_facts(phone="+94 77 999 0000")  # snippet still says the real number
    verdict = validate(make(facts=facts))
    assert verdict.verdict == "revise"
    v = next(v for v in verdict.violations if v.code == "UNSUPPORTED_CONTACT")
    assert v.field == "phone" and v.target == "gym_analysis"


def test_fabricated_snippet_not_in_retrieved_text_is_rejected():
    evidence = [e.model_dump() for e in golden_facts().evidence]
    for e in evidence:
        if e["field"] == "email":
            e["snippet"] = "reach us at boss@fitzone.lk"
    facts = golden_facts(email="boss@fitzone.lk", evidence=evidence)
    assert "UNSUPPORTED_CONTACT" in codes(validate(make(facts=facts)))


def test_contact_matching_trusted_known_value_is_accepted_without_evidence():
    gym = gym_request(known_phone="+94 11 000 0000")
    facts = golden_facts(phone="+94 11 000 0000")
    assert "UNSUPPORTED_CONTACT" not in codes(validate(make(facts=facts, gym=gym)))


def test_malformed_email_and_phone():
    assert "INVALID_FORMAT" in codes(validate(make(facts=golden_facts(email="not-an-email"))))
    assert "INVALID_FORMAT" in codes(validate(make(facts=golden_facts(phone="12"))))


def test_equipment_without_evidence_is_flagged():
    facts = golden_facts(evidence=[e for e in golden_facts().model_dump()["evidence"] if e["field"] != "equipment"])
    assert "UNSUPPORTED_ITEMS" in codes(validate(make(facts=facts)))


def test_low_confidence_triggers_revision():
    verdict = validate(make(facts=golden_facts(confidence=0.4)))
    assert verdict.verdict == "revise" and "LOW_CONFIDENCE" in codes(verdict)


def test_no_usable_data_is_rejected_outright():
    facts = golden_facts(equipment=[], classes=[], phone=None, email=None, opening_hours=None, evidence=[], confidence=0.1)
    assert validate(make(facts=facts, corpus=[])).verdict == "reject"


def test_workout_using_equipment_the_gym_does_not_have():
    recs = golden_recs(workouts=[workout("Rowing", used=("rowing machine",))] + golden_recs().workouts[1:])
    verdict = validate(make(recs=recs))
    v = next(v for v in verdict.violations if v.code == "UNKNOWN_EQUIPMENT")
    assert v.target == "workout_recommendation"


def test_plural_and_singular_equipment_names_match():
    recs = golden_recs(workouts=[workout("Squats", used=("squat racks",))] + golden_recs().workouts[1:])
    assert "UNKNOWN_EQUIPMENT" not in codes(validate(make(recs=recs)))


def test_wrong_workout_count_and_duplicates():
    three = golden_recs().workouts[:3]
    assert "WRONG_COUNT" in codes(validate(make(recs=golden_recs(workouts=three))))
    dup = golden_recs().workouts[:3] + [golden_recs().workouts[0]]
    assert "DUPLICATE_NAME" in codes(validate(make(recs=golden_recs(workouts=dup))))


def test_duration_category_bounds():
    bad = [workout("Marathon", minutes=300)] + golden_recs().workouts[1:]
    assert "DURATION_RANGE" in codes(validate(make(recs=golden_recs(workouts=bad))))
    bad = [workout("Pilates", category="Core")] + golden_recs().workouts[1:]
    assert "BAD_CATEGORY" in codes(validate(make(recs=golden_recs(workouts=bad))))


def test_unsafe_medical_claims_are_blocked():
    w = workout("Miracle Burn")
    w["description"] = "This routine will cure back pain, guaranteed."
    recs = golden_recs(workouts=[w] + golden_recs().workouts[1:])
    assert "UNSAFE_CONTENT" in codes(validate(make(recs=recs)))


def test_beginner_limits():
    long_beginner = [workout("Long", minutes=90, difficulty="Beginner")] + golden_recs().workouts[1:]
    assert "BEGINNER_TOO_LONG" in codes(validate(make(recs=golden_recs(workouts=long_beginner))))
    w = workout("Test Day", difficulty="Beginner")
    w["description"] = "Work up to a one-rep max on squats."
    assert "BEGINNER_TOO_INTENSE" in codes(validate(make(recs=golden_recs(workouts=[w] + golden_recs().workouts[1:]))))


# ── URL allow-list ──────────────────────────────────────────────────────


def with_evidence_url(url, fields=None):
    """Golden facts whose evidence all cite `url` (optionally only for some fields)."""
    evidence = [e.model_dump() for e in golden_facts().evidence]
    for e in evidence:
        if fields is None or e["field"] in fields:
            e["source_url"] = url
    return golden_facts(evidence=evidence)


def violation(verdict, code):
    return next(v for v in verdict.violations if v.code == code)


def test_own_site_citation_with_a_different_spelling_is_accepted():
    facts = with_evidence_url("http://www.fitzone.lk/")            # scheme, www, trailing slash differ
    assert validate(make(facts=facts)).verdict == "pass"


def test_allow_listed_site_that_was_retrieved_is_accepted():
    page = "https://m.facebook.com/fitzone"
    assert validate(make(facts=with_evidence_url(page), retrieved=[page])).verdict == "pass"


def test_missing_source_url_is_revise():
    evidence = [{**e.model_dump(), "source_url": None} for e in golden_facts().evidence]
    verdict = validate(make(facts=golden_facts(evidence=evidence)))
    v = violation(verdict, "EVIDENCE_URL_MISSING")
    assert (verdict.verdict, v.severity, v.target) == ("revise", "revise", "gym_analysis")


@pytest.mark.parametrize(
    "url",
    ["http://facebook.com/fitzone", "https://user:pw@fitzone.lk", "https://127.0.0.1/x", "ftp://fitzone.lk", "https://fitzone.lk:8443/"],
)
def test_malformed_or_unsafe_source_url_is_revise(url):
    verdict = validate(make(facts=with_evidence_url(url), retrieved=[url]))
    assert verdict.verdict == "revise" and "EVIDENCE_URL_INVALID" in codes(verdict)


@pytest.mark.parametrize("url", ["https://random-blog.example/fitzone", "https://evilfacebook.com/x", "https://facebook.com.evil.com/x"])
def test_source_url_off_the_allow_list_is_revise(url):
    verdict = validate(make(facts=with_evidence_url(url), retrieved=[url]))
    assert verdict.verdict == "revise" and "EVIDENCE_URL_NOT_ALLOWED" in codes(verdict)
    assert violation(verdict, "EVIDENCE_URL_NOT_ALLOWED").target == "gym_analysis"


def test_allowed_host_but_page_never_retrieved_is_revise():
    verdict = validate(make(facts=with_evidence_url("https://fitzone.lk/secret-page")))
    assert verdict.verdict == "revise" and "EVIDENCE_URL_NOT_RETRIEVED" in codes(verdict)


def test_claims_backed_only_by_untrusted_urls_count_as_unsupported():
    # The snippet text is real, but it is cited to a URL that is not allowed, so it proves nothing.
    verdict = validate(make(facts=with_evidence_url("https://random-blog.example/x", ["phone"]), retrieved=[WEBSITE, "https://random-blog.example/x"]))
    assert "UNSUPPORTED_CONTACT" in codes(verdict) and "EVIDENCE_URL_NOT_ALLOWED" in codes(verdict)


def test_url_violations_are_not_repeated_per_snippet():
    verdict = validate(make(facts=with_evidence_url("https://random-blog.example/x"), retrieved=["https://random-blog.example/x"]))
    fields = [v.field for v in verdict.violations if v.code == "EVIDENCE_URL_NOT_ALLOWED"]
    assert len(fields) == len(set(fields)) == 5                  # one per evidence field, not more


def test_custom_allow_list_is_honoured(monkeypatch):
    page = "https://gymdb.io/fitzone"
    facts = with_evidence_url(page)
    assert "EVIDENCE_URL_NOT_ALLOWED" in codes(validate(make(facts=facts, retrieved=[page])))
    monkeypatch.setenv("GYM_URL_ALLOWLIST", "gymdb.io")
    assert validate(make(facts=facts, retrieved=[page])).verdict == "pass"


def test_gym_without_a_website_can_only_cite_allow_listed_sites():
    gym = gym_request(website=None)
    verdict = validate(make(gym=gym, facts=with_evidence_url(WEBSITE), retrieved=[WEBSITE]))
    assert "EVIDENCE_URL_NOT_ALLOWED" in codes(verdict)          # fitzone.lk is not "own" here
    page = "https://tripadvisor.com/fitzone"
    assert validate(make(gym=gym, facts=with_evidence_url(page), retrieved=[page])).verdict == "pass"


@pytest.mark.parametrize("website", ["http://127.0.0.1:8000", "https://user:pw@fitzone.lk", "http://169.254.169.254", "ftp://fitzone.lk"])
def test_unusable_request_website_is_an_immediate_reject(website):
    verdict = validate(make(gym=gym_request(website=website)))
    v = violation(verdict, "REQUEST_WEBSITE_INVALID")
    assert (verdict.verdict, v.severity) == ("reject", "reject")


# ── business rules: reject vs revise ────────────────────────────────────


def empty_facts(confidence):
    return golden_facts(equipment=[], classes=[], phone=None, email=None, opening_hours=None, evidence=[], confidence=confidence)


def test_empty_result_is_never_a_pass_even_at_good_confidence():
    verdict = validate(make(facts=empty_facts(0.9)))
    assert verdict.verdict == "revise" and "NO_EQUIPMENT_OR_CLASSES" in codes(verdict)
    assert violation(verdict, "NO_EQUIPMENT_OR_CLASSES").target == "gym_analysis"


def test_empty_result_with_almost_no_confidence_is_rejected_outright():
    verdict = validate(make(facts=empty_facts(0.1), corpus=[]))
    assert verdict.verdict == "reject" and codes(verdict) == {"NO_USABLE_DATA"}


def test_a_reject_wins_over_revise_violations():
    verdict = validate(make(gym=gym_request(website="http://127.0.0.1"), facts=with_evidence_url("https://random-blog.example/x")))
    assert verdict.verdict == "reject"
    assert {"REQUEST_WEBSITE_INVALID", "EVIDENCE_URL_NOT_ALLOWED"} <= codes(verdict)


def test_only_unfixable_problems_are_severity_reject():
    everything = [
        validate(make(facts=empty_facts(0.9))),
        validate(make(facts=with_evidence_url("https://random-blog.example/x"))),
        validate(make(recs=golden_recs(workouts=golden_recs().workouts[:3]))),
        validate(make(facts=golden_facts(confidence=0.3))),
    ]
    assert all(v.severity == "revise" for verdict in everything for v in verdict.violations)


def test_duplicate_and_oversized_lists():
    dup = golden_facts(equipment=["Treadmill", "treadmill ", "dumbbell"])
    assert "DUPLICATE_ITEMS" in codes(validate(make(facts=dup)))
    many = golden_facts(equipment=[f"machine {i}" for i in range(41)])
    verdict = validate(make(facts=many))
    assert violation(verdict, "TOO_MANY_ITEMS").field == "equipment"
    assert "DUPLICATE_ITEMS" not in codes(verdict)


def test_verdict_and_severity_are_serialised_for_the_audit_trail():
    verdict = validate(make(gym=gym_request(website="http://127.0.0.1")))
    dumped = verdict.model_dump(mode="json")
    assert dumped["violations"][0]["severity"] == "reject" and dumped["verdict"] == "reject"
