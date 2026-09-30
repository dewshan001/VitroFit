"""Latency smoke tests: small runs of the measurements in perf/measure_latency.py with generous limits.

Run on purpose:  pytest -m perf
The limits are several times what a normal machine needs, so they only fail on a real regression (for
example an accidentally quadratic scan, a missing index, or a hung workflow), not on a slow CI runner.
Any failed request or workflow fails the test whatever the speed. Full numbers: python -m perf.measure_latency.
"""

import asyncio

import pytest
from langgraph.checkpoint.memory import MemorySaver

from perf import measure_latency as m

pytestmark = pytest.mark.perf


@pytest.fixture(autouse=True)
def fresh_db():
    yield                                        # these tests create their own rows; no per-test table reset needed


def test_components_stay_cheap():
    result = m.bench_components(n=30)
    assert result["injection guard, clean 6,000-char page"]["p95"] < 100          # normally ~3 ms
    assert result["injection guard, hostile 6,000-char page"]["p95"] < 100
    assert result["validator, golden output"]["p95"] < 100                        # normally ~1 ms
    assert result["planner"]["p95"] < 10


def test_the_guard_scales_roughly_linearly_with_page_size():
    import time

    import injection_guard

    unit = "Treadmills dumbbells squat racks yoga spin classes open daily from six. "

    def cost(chars: int) -> float:
        page = (unit * (chars // len(unit) + 1))[:chars]
        started = time.perf_counter()
        for _ in range(10):
            injection_guard.guard_text(page, limit=chars)
        return time.perf_counter() - started

    small, large = cost(1500), cost(6000)
    assert large < small * 12          # 4x the text: allow up to 12x (a quadratic scan would be about 16x)


def test_database_operations_stay_fast():
    from db import engine

    if engine.dialect.name == "sqlite":
        pytest.skip("database timings are only meaningful on PostgreSQL (run with TEST_DATABASE_URL)")
    result = m.bench_database(n=20)
    for name, stats in result.items():
        assert stats["p95"] < 250, f"{name} p95 {stats['p95']} ms"                # normally 1-5 ms


def test_concurrent_workflows_all_complete_and_publish():
    result = asyncio.run(m.bench_workflows(MemorySaver(), levels=(1, 10), per_level=10))
    for name, stats in result.items():
        assert stats["failures"] == 0, f"{name}: {stats['failures']} failed"
        assert stats["p95"] < 20_000, f"{name} p95 {stats['p95']} ms"            # normally well under a second


def test_http_api_answers_every_request_at_concurrency():
    result = asyncio.run(m.bench_http(MemorySaver(), levels=(1, 10), requests_per_level=30))
    assert result["wrong service key is refused"] == 401
    for level, cases in result.items():
        if isinstance(cases, dict):
            for name, stats in cases.items():
                assert stats["failures"] == 0, f"{level} {name}: {stats['failures']} failed"
                assert stats["p95"] < 5_000, f"{level} {name} p95 {stats['p95']} ms"


def test_statistics_helper_is_correct():
    stats = m.summarise([float(i) for i in range(1, 101)])
    assert (stats["n"], stats["p50"], stats["p95"], stats["p99"], stats["max"]) == (100, 50.0, 95.0, 99.0, 100.0)
    assert m.summarise([]) == {"n": 0}
    assert m.summarise([7.0])["p99"] == 7.0


def test_the_load_helper_counts_failures_and_respects_concurrency():
    seen = {"now": 0, "peak": 0}

    async def job(i: int):
        seen["now"] += 1
        seen["peak"] = max(seen["peak"], seen["now"])
        await asyncio.sleep(0.005)
        seen["now"] -= 1
        if i % 4 == 0:
            raise RuntimeError("boom")
        return True

    result = asyncio.run(m.run_load(20, 5, job))
    assert result["failures"] == 5 and result["success_rate"] == 75.0 and result["n"] == 15
    assert seen["peak"] <= 5


def test_live_mode_is_refused_without_the_explicit_environment_switch(monkeypatch):
    monkeypatch.delenv("GYM_PERF_ALLOW_LIVE", raising=False)
    args = m.parse_args(["--live", "--sections", "components", "--database-url", "sqlite:///x.db"])
    with pytest.raises(SystemExit, match="GYM_PERF_ALLOW_LIVE=1"):
        asyncio.run(m.main_async(args))


def test_database_sections_need_a_database_url():
    args = m.parse_args(["--sections", "database"])
    args.database_url = None
    with pytest.raises(SystemExit, match="--database-url"):
        asyncio.run(m.main_async(args))
