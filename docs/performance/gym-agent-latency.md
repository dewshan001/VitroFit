# Gym agent service: latency and load report

Produced with `python -m perf.measure_latency` (see `BackendAPI/GymAgentService/perf/README.md`). All numbers below were
measured on the development machine described in the header of the tables; none are estimates. To regenerate them, run the
tool against a scratch PostgreSQL database.

## What the numbers say

1. **Our own code is cheap.** The injection guard takes 2.5 to 2.6 ms (p50) for a 6,000-character page (2.64 ms clean, 2.53 ms hostile); the validator
   takes 0.84 ms; the planner, URL policy and contract parsing take 0.02 ms or less. Next to an LLM call (tens of seconds) they are
   negligible.
2. **The database is not a bottleneck.** A bare round trip is 0.40 ms (p50). The store operations take 1 to 3 ms (p50): create a workflow
   0.96 ms, read one with its 6 steps and 12 tool calls 1.5 ms, the event timeline 1.1 ms, list 50 workflows 1.7 ms, record an agent step with
   two tool calls and the state update in one transaction 2.6 ms, publish (approval check plus the verified write in one transaction)
   3.1 ms, read a paused workflow's checkpoint 0.78 ms.
3. **Whole workflows all succeed, and throughput levels off.** 90 complete workflows (plan, delegate, validate, pause, approve, publish)
   ran at concurrency 1, 5, 10 and 25 with **0 failures (100% success)**. Throughput rises from 14.7 to about 18.7 workflows per second and
   then stops growing, so latency rises with concurrency: p50 68 ms at concurrency 1, 517 ms at 10, 1.29 s at 25. The service is the limit on
   this machine; I did not profile why. This is irrelevant to the expected use (an administrator reviewing a few gyms a day), and the scripted
   model here answers instantly, so in real use the LLM, not this ceiling, sets the pace.
4. **The internal HTTP API answers everything it is asked.** Through an in-process client, reading a workflow takes 3.0 ms (p50) and its
   events 4.2 ms at concurrency 1, with about 320 requests per second; there were **0 failed requests** at concurrency 1, 10 and 50, and a wrong
   service key was refused with HTTP 401. **The list endpoint is the heaviest call** (12.8 ms p50, about 60 to 70 requests per second, 0.70 s p50
   at 50 concurrent) because it returns 50 complete rows including the plan, facts and recommendations. A summary-only list would be cheaper;
   this has not been changed.
5. **Real LLM latency dominates everything** (from runs stored earlier; small samples, see `n`). The gym analysis agent took 61.0 s (p50,
   n=4) and the workout recommendation agent 30.9 s (p50, n=4). The two LLM-backed agents account for **95.8% of a run's time**. A search call took
   4.3 s (p50, n=6). A whole completed run took 97.2 s (p50, n=3; the slowest, 200.5 s, included a revision).
6. **The first use after a service start is slow.** In the stored runs, the publish step took 7.9 s (p50) and one similar-gym lookup 14.5 s, although
   the database part of publishing takes about 3 ms. Both use the local embedding model. Timed separately in a fresh process, the first
   construction of that model took 8.9 to 9.1 s and later ones 0.14 to 0.17 s. So the first approval or lookup after each start pays about
   9 s. Not fixed. A straightforward improvement is to load the model in the background at startup and reuse one instance.

## Limits of these measurements

- One machine, one run, so expect variation of tens of percent between runs. Timings were taken with service logging at WARNING level
  (production logs at INFO, which costs tens of microseconds per line).
- The component, database, workflow and HTTP sections use a scripted instant model, so they measure our code and database only.
- The HTTP section does not include the network or the ASP.NET hop. No measurement through ASP.NET was made.
- The real LLM figures come from very few stored runs (2 to 6 samples per row) and from one provider configuration; they show the order of
  magnitude, not a distribution. A live sample can be taken with `--live` (opt-in, uses API quota); none was taken for this report.

## Measurements

Measured 2026-09-30 05:49 UTC on Windows-11-10.0.26200-SP0, Python 3.12.7, 12 CPUs, PostgreSQL 18.4, LangGraph 1.2.11, FastAPI 0.141.1, SQLAlchemy 2.0.53.

The model is scripted (instant) in the component, database, workflow and HTTP sections, so those numbers are the cost of our own code and database, not of an LLM. Real LLM timings are in the last section, read from runs stored earlier.

### Components (no I/O)

| Measurement | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
| injection guard, clean 6,000-char page | 500 | 2.764 | 2.643 | 3.628 | 4.709 | 5.346 |
| injection guard, hostile 6,000-char page | 500 | 2.629 | 2.525 | 3.117 | 4.051 | 4.644 |
| injection scan, short field | 500 | 0.021 | 0.02 | 0.028 | 0.032 | 0.05 |
| validator, golden output | 500 | 0.871 | 0.842 | 1.047 | 1.25 | 1.589 |
| URL policy (check + key) | 500 | 0.012 | 0.012 | 0.013 | 0.015 | 0.021 |
| planner | 500 | 0.007 | 0.006 | 0.016 | 0.019 | 0.056 |
| output contract parse (GymFacts) | 500 | 0.006 | 0.006 | 0.006 | 0.006 | 0.013 |

### Database (PostgreSQL, same machine)

| Measurement | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
| round trip (SELECT 1) | 200 | 0.398 | 0.397 | 0.491 | 0.539 | 0.601 |
| create workflow | 200 | 0.986 | 0.96 | 1.241 | 1.56 | 1.764 |
| record node (step + 2 tool calls + state, one transaction) | 200 | 2.651 | 2.603 | 3.321 | 3.647 | 3.927 |
| get workflow (with 6 steps, 12 tool calls) | 200 | 1.572 | 1.535 | 1.861 | 1.937 | 1.965 |
| events timeline | 200 | 1.124 | 1.087 | 1.358 | 1.53 | 1.611 |
| list workflows (limit 50) | 200 | 1.776 | 1.722 | 2.176 | 2.321 | 2.481 |
| publish (approval check + verified write, one transaction) | 100 | 3.156 | 3.053 | 3.807 | 4.554 | 8.571 |
| read paused workflow state (checkpointer) | 200 | 0.824 | 0.78 | 1.042 | 1.113 | 2.284 |

### Whole workflows (scripted model, real graph and database)

Each workflow runs planner, gym analysis, workout recommendation and validator, pauses for approval, is approved, and is published as verified.

| Case | requests | failures | success % | per second | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| concurrency 1 | 10 | 0 | 100.0 | 14.73 | 67.738 | 76.554 | 76.554 | 76.554 |
| concurrency 5 | 10 | 0 | 100.0 | 16.48 | 264.245 | 413.143 | 413.143 | 413.143 |
| concurrency 10 | 20 | 0 | 100.0 | 18.45 | 516.617 | 658.315 | 671.634 | 671.634 |
| concurrency 25 | 50 | 0 | 100.0 | 18.72 | 1291.402 | 1571.662 | 1600.301 | 1600.301 |

Time inside the service per phase:

| Concurrency | start to awaiting approval p50 / p95 ms | approve to published p50 / p95 ms |
|---|---:|---:|
| concurrency 1 | 36.823 / 39.694 | 17.834 / 25.943 |
| concurrency 5 | 154.746 / 195.031 | 57.93 / 116.52 |
| concurrency 10 | 322.547 / 367.352 | 128.075 / 199.962 |
| concurrency 25 | 770.744 / 934.29 | 408.965 / 504.243 |

### Internal HTTP API (in-process ASGI client)

Measures the service's request handling and database queries. It does not include the network or the ASP.NET hop.

**concurrency 1**

| Case | requests | failures | success % | per second | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GET workflow | 100 | 0 | 100.0 | 323.55 | 3.028 | 3.583 | 3.731 | 4.244 |
| GET events | 100 | 0 | 100.0 | 234.35 | 4.152 | 4.781 | 5.628 | 5.716 |
| GET list (limit 50) | 100 | 0 | 100.0 | 72.04 | 12.756 | 13.95 | 15.436 | 103.763 |
| POST start workflow (returns 202) | 20 | 0 | 100.0 | 88.37 | 9.904 | 15.568 | 16.194 | 16.194 |

**concurrency 10**

| Case | requests | failures | success % | per second | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GET workflow | 100 | 0 | 100.0 | 336.23 | 19.863 | 69.742 | 97.306 | 106.354 |
| GET events | 100 | 0 | 100.0 | 287.03 | 27.945 | 80.831 | 110.256 | 118.328 |
| GET list (limit 50) | 100 | 0 | 100.0 | 58.58 | 143.656 | 235.195 | 249.738 | 251.234 |
| POST start workflow (returns 202) | 20 | 0 | 100.0 | 95.57 | 42.496 | 129.552 | 206.392 | 206.392 |

**concurrency 50**

| Case | requests | failures | success % | per second | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| GET workflow | 200 | 0 | 100.0 | 316.34 | 132.088 | 228.864 | 241.283 | 245.201 |
| GET events | 200 | 0 | 100.0 | 319.61 | 144.054 | 198.444 | 238.271 | 239.235 |
| GET list (limit 50) | 200 | 0 | 100.0 | 62.87 | 699.396 | 915.343 | 1084.156 | 1182.231 |
| POST start workflow (returns 202) | 50 | 0 | 100.0 | 124.76 | 101.727 | 170.609 | 389.018 | 389.018 |

A wrong service key is refused with HTTP 401.

### Agentic AI latency (real LLM, from stored runs)

Real timings from runs stored earlier (read-only; small samples, see n). Agent steps include the LLM calls made inside them.

Workflows by status: {'AwaitingApproval': 1, 'Published': 2, 'Failed': 2}. Share of run time spent in the two LLM-backed agents: 95.8%.

Per agent step:

| Measurement | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
| approval_gate | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| gym_analysis | 4 | 58692.5 | 60992.0 | 66371.0 | 66371.0 | 66371.0 |
| planner | 5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| publish | 2 | 8272.0 | 7892.0 | 8652.0 | 8652.0 | 8652.0 |
| safe_fail | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| validator | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| workout_recommendation | 4 | 35504.25 | 30863.0 | 46183.0 | 46183.0 | 46183.0 |

Per tool call:

| Measurement | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
| list_equipment_taxonomy | 4 | 0.5 | 0.0 | 1.0 | 1.0 | 1.0 |
| lookup_similar_gyms | 1 | 14478.0 | 14478.0 | 14478.0 | 14478.0 | 14478.0 |
| search_gym_info | 6 | 4296.5 | 4267.0 | 6017.0 | 6017.0 | 6017.0 |

Whole run (sum of steps):

| Measurement | n | mean ms | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|---:|
| completed runs | 3 | 131110.333 | 97234.0 | 200536.0 | 200536.0 | 200536.0 |
