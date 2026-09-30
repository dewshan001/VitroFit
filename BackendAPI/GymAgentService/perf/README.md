# Latency and load measurements

`measure_latency.py` measures the gym agent service and writes `latest.json` and `latest.md` (default
`reports/perf/`, git-ignored). Every number in a report comes from an actual run of this tool.

```bash
# from BackendAPI/GymAgentService, with a SCRATCH PostgreSQL database (the sections create and delete rows)
python -m perf.measure_latency --database-url postgresql+psycopg2://user:pw@localhost:5432/gym_perf
python -m perf.measure_latency --database-url ... --quick          # about 10x fewer iterations
python -m perf.measure_latency --sections components,stored        # no database needed
```

| Section | What it measures | Model |
|---|---|---|
| `components` | injection guard, validator, URL policy, planner, contract parsing (no I/O) | none |
| `database` | workflow store round trips on PostgreSQL, and reading the checkpointed state | none |
| `workflows` | whole four-agent workflows (plan, delegate, validate, pause, approve, publish) at concurrency 1, 5, 10, 25: latency percentiles, throughput, success rate | scripted, instant |
| `http` | the internal HTTP API through an in-process ASGI client at concurrency 1, 10, 50 | scripted, instant |
| `stored` | **real LLM timings**, read from the steps and tool calls already stored by earlier runs (read-only connection, no new LLM or web calls) | real (recorded earlier) |

Because the model is scripted in most sections, those numbers are the cost of our own code and database. The
`stored` section is where LLM latency shows. The `http` section does not include the network or the ASP.NET hop.

## Live runs (opt-in)

`--live` runs real workflows against the configured LLM and web search. It uses API quota, so it needs both the
flag and `GYM_PERF_ALLOW_LIVE=1`:

```bash
GYM_PERF_ALLOW_LIVE=1 python -m perf.measure_latency --database-url ... --sections components --live --live-runs 3 --live-gym-name "FitZone" --live-website https://fitzone.lk
```

## Smoke tests

`tests/perf/test_latency_smoke.py` (`pytest -m perf`) runs small versions of the same measurements with limits
several times what a normal machine needs. They fail on a real regression (for example a missing index or a hung
workflow) or on any failed request, not on a slow CI runner. CI runs them against PostgreSQL.
