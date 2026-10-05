from tests.evaluation.report import RESULTS, write_reports


def pytest_sessionfinish(session, exitstatus):
    """After the run, write evaluation_report.md/json (reports/ by default, or $EVAL_REPORT_DIR)."""
    if RESULTS:
        write_reports()
