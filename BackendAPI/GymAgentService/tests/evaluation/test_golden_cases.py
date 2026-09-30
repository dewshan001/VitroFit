import pytest

from tests.evaluation.cases import CASES, CRITERIA
from tests.evaluation.harness import evaluate, run_case
from tests.evaluation.report import RESULTS

pytestmark = pytest.mark.evaluation


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_golden_case(case, monkeypatch):
    outcome = run_case(case, monkeypatch)
    checks = evaluate(case, outcome)
    RESULTS.extend(checks)                       # recorded first, so a failing case still appears in the report

    failed = [c for c in checks if not c.passed]
    assert not failed, "\n".join(
        f"[{c.criterion}] {c.name}: expected {c.expected!r}, observed {c.observed!r}" for c in failed
    )


def test_every_required_criterion_is_evidenced_by_a_golden_case():
    """The assignment lists what an evaluation must show. If a criterion has no case, the suite is incomplete."""
    covered = {e.criterion for c in CASES for e in c.expects} | {"structured_outputs"}   # structured outputs are checked on every case
    assert set(CRITERIA) <= covered, f"no golden case evidences: {sorted(set(CRITERIA) - covered)}"


def test_every_case_has_at_least_one_expectation_and_a_unique_id():
    assert all(c.expects for c in CASES)
    assert len({c.id for c in CASES}) == len(CASES)


def test_the_report_marks_a_failing_check_as_a_failure():
    from tests.evaluation.harness import Check
    from tests.evaluation.report import build_markdown

    text = build_markdown([Check("G01-approved-and-published", "approval_enforcement", "status", "Published", "Failed", False)], "now")
    assert "| FAIL |" in text and "**FAIL**" in text and "0 of 1 checks passed" in text
