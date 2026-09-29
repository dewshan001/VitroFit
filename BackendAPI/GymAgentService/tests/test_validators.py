from agents import planner
from contracts import ValidatorInput
from tests.support import SITE_TEXT, golden_facts, golden_recs, gym_request, workout
from validators import validate


def make(facts=None, recs=None, corpus=None, gym=None):
    gym = gym or gym_request()
    return ValidatorInput(
        gym=gym,
        plan=planner.run(gym),
        facts=facts or golden_facts(),
        recommendations=recs or golden_recs(),
        corpus=[SITE_TEXT] if corpus is None else corpus,
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
