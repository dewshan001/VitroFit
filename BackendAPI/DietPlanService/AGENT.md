# Diet Plan Agent — Multi-Agent Workflow

## How I explain it in 60 seconds

My Diet Planning workflow has three agents with different jobs. A small coordinator (`workflow.py`) builds a plan of steps and hands each one to the right agent. Each agent can use only its own approved tools — the Meal Generator is the only one allowed to call the LLM, and it can't touch the database. The Safety Validator checks the finished meals against fixed rules, not AI — calorie tolerance, allergy/restriction keywords, medical-condition sanity checks. If validation says "revise" (a tolerance miss, nothing unsafe), the coordinator sends the specific problems back to the Meal Generator for one more attempt (2 total tries); if it's still not within tolerance after that, we hand back the closest attempt flagged as not-quite-on-target rather than nothing at all. Only a genuine safety issue — a restricted/allergy ingredient, or calories under a safe floor — is a hard "reject" with no plan returned. If a plan is classified high-impact — under a safe calorie floor, or a minor with a medical condition — it pauses and waits for a Trainer or Admin to approve it before it can be saved. Every step, tool call, retry, and decision is logged to a `diet_workflows` row, so the whole run is traceable end to end.

## Flow

```
Request -> Coordinator builds plan
   Step 1  Nutrition Analyst   -> targets + risk level          (tools: calculate_targets, assess_risk, lookup_budget)
   Step 2  Meal Generator      -> meals (LLM)                   (tool:  generate_meals)
   Step 3  Safety Validator    -> pass / revise / reject        (tool:  validate_plan, rules only)
              revise -> back to Meal Generator (1 retry, 2 tries total)
                        still revising after that -> completed with withinTolerance=false (best-effort, not blocked)
              reject  -> hard stop, no plan returned (safety issue: restriction/allergy/calorie floor)
   Step 4  Risky plan? -> wait for Trainer/Admin approval -> save plan
   (every step is logged to the workflow record)
```

## The three agents

| Agent | Responsibility | Input | Output | Allowed tools |
|---|---|---|---|---|
| **Nutrition Analyst** | Domain analysis: deterministic targets, risk classification, budget grounding | profile, goal, medical conditions, budget tier | `targets` (calories/macros), `risk_level`, `risk_flags`, `budget_context` | `calculate_targets`, `assess_risk`, `lookup_budget` |
| **Meal Generator** | Action / tool use: generates a day's meals via the LLM | targets, restrictions, dislikes, medical conditions, budget context, cooking time, optional revision feedback | strict `meals` schema, `withinTolerance` | `generate_meals` (no DB access) |
| **Safety Validator** | Validation / safety: fixed rule checks, no AI | meals, targets, preferences | `verdict` (pass/revise/reject), itemised `violations` | `validate_plan` |

The LLM never computes calories or macros — `calculator.py` is the only source of those numbers; the Meal Generator only fills in food items to match a target it's given.

## Requirements → implementation

| Requirement | Where |
|---|---|
| 1. Objective → structured multi-step plan, delegated per step | `workflow.build_plan()`, `workflow.run_workflow()` |
| 2. Three genuinely distinct agents, own I/O contracts, own tools, own log entries | `agents.py` (3 classes), `workflow.call_tool()` events |
| 3. Allow-listed tools, validated inputs, structured outputs, error handling | `agents.py` (`allowed_tools`, Pydantic models), `workflow.call_tool()` |
| 4. Durable workflow state (plan, steps, tool results, validation, errors, approval, outcome) | `workflow_models.py` (`diet_workflows` table) |
| 5. Deterministic validation before acceptance; bad output revised/rejected | `validators.py`, `workflow.run_workflow()`'s revise/reject branches |
| 6. High-impact action pauses for approval | `agents._assess_risk()`, `main.py` `/workflows/{id}/approve`, `/reject`, `approval_status` |
| 7. Auditable trace (agent runs, tool calls, timings, validation, errors, retries, approval, outcome) | `workflow.call_tool()` events, `DietWorkflow.events`/`.completed_steps`, `GET /workflows/{id}/trace` |
| 8. Security: RBAC, input/output validation, secret protection, timeouts, retry limit, safe failure | `security.require_roles`, `main.py` `Literal` enums, `auth.py` (secret from `VitroFit.API`, no logging), `workflow.py` (`_TOOL_TIMEOUTS`, `_MAX_REVISE_RETRIES`, `_OVERALL_TIME_BUDGET_SECONDS`) |

## Calling this from other services

- `POST /api/diet/generate` (JWT required) — starts the workflow and returns **immediately** (typically <1s) with `{workflowId, status: "running", plan}`. It does not wait for the LLM. Poll `GET /api/diet/workflows/{workflowId}` to watch live progress and get the finished plan.
- `GET /api/diet/workflows/{workflowId}` — full detail (owner, or Trainer/Admin): `status`, `completedSteps` (grows in real time as each agent finishes), `targets`, `meals`, `finalOutcome`, and — once terminal — a customer-facing `message` on `failed`/`rejected`.
- `GET /api/diet/workflows/{workflowId}/trace` — ordered `events` + `completedSteps`, showing exactly which agent ran which tool, when, and whether it succeeded.
- `GET /api/diet/approvals/pending`, `POST /api/diet/workflows/{id}/approve`, `POST /api/diet/workflows/{id}/reject` — Trainer/Admin only.
- `POST /api/diet/confirm` accepts an optional `workflowId`; when given, it persists the workflow's own stored, validated data (ignoring anything the client sends for those fields) rather than trusting client-submitted plan data. Requires the referenced workflow to be `completed` first.
- `POST /api/diet/workflows/{workflowId}/refine` (owner only) — body `{instruction: "instead of rice, include something else at lunch"}`. Applies one free-text edit to an already-completed workflow's plan, instead of the user regenerating from scratch through the preferences form. Same start-now/poll pattern as `/generate`: returns `{workflowId, status: "running"}` immediately, runs in the background (`workflow.execute_refine`), poll the same `GET /workflows/{id}`. Requires the workflow to be `completed`.

Status values: `running` → `completed` | `failed` | `rejected`. Approval values: `pending` → `approved` | `rejected`, or `auto_approved` for standard-risk plans.

**How refine stays safe.** The instruction is sent to the LLM as data (`userRequestedChange` in the JSON prompt, never concatenated into the system prompt), with the system instruction explicit that it can't override restrictions/dislikes/medical conditions/targets - that's the first layer. The real guarantee is the second layer: every refined plan still goes through the Safety Validator exactly like a fresh generation, regardless of what the LLM did. If the edit would violate a restriction or safety rule, the workflow reverts to the plan's previous meals (never partially applies an unsafe edit) and `message`/`wf.error` explains why. A tolerance-only miss (not a safety issue) still applies the edit, same soft-degrade philosophy as initial generation.

**Architecture note (superseding the original "additive-only" constraint, with the user's explicit go-ahead):** `/generate` used to run the whole workflow inline and block until done, returning the finished plan directly (`totalCalories`/`macros`/`meals`/`withinTolerance` at the top level). It now starts the workflow in a detached background task (`workflow.execute_workflow`, its own DB session via `create_workflow()`+`asyncio.create_task()`) and returns the `workflowId` right away, so the frontend can poll and show each agent's real progress live instead of staring at a spinner for up to `_OVERALL_TIME_BUDGET_SECONDS`. `VitroFit_web/src/api/dietPlan.js`'s `pollDietWorkflow()` is the reference client implementation. This is a genuine breaking change to `/generate`'s response shape (no longer additive) — any other caller of this endpoint needs to switch to the start-then-poll pattern.

## Known tradeoffs / judgment calls

- **230s workflow budget, run in the background, not inline.** `execute_workflow()` can legitimately take close to `_OVERALL_TIME_BUDGET_SECONDS` (230s) to reach a terminal status, because `meal_agent.generate_meals()` measured 65-118s per successful call against the live NVIDIA endpoint (`meal_agent._CALL_TIMEOUT_SECONDS` raised 40s -> 70s per attempt to match, up to three attempts = 210s worst case). This used to mean `/generate` itself blocked for that long; it no longer does — `/generate` returns the `workflowId` in well under a second, and `execute_workflow()` runs as a detached background task while the frontend polls `/workflows/{id}` for live progress. If the NVIDIA model response time improves (e.g. switching `NVIDIA_MODEL_PRIMARY` to a smaller/faster model), the timeout constants in `meal_agent.py` and `workflow.py` can be lowered.
- **`requiresApproval` triggers only on `risk_level == "high"`**, not `"medium"` — otherwise every under-18 user or anyone with a mild medical condition would always block on a trainer. This threshold is a judgment call and easy to tighten later (`agents._assess_risk`).
- **A "revise" verdict soft-degrades instead of hard-failing once retries are exhausted.** Only a genuine "reject" verdict (a restriction/allergy conflict, or calories under the safe floor) blocks the user with no plan. A tolerance miss after the retry limit still returns the closest attempt with `withinTolerance: false`, matching how `/generate` behaved before this workflow existed (a warning banner, never a dead end).
- **Known, pre-existing, deliberately untouched issues:** `db.py`'s hardcoded fallback DB password and the git-tracked `.env` file; the frontend's default API port (8002) doesn't match `.env.example`'s `PORT=8003`. Both were flagged and left alone per explicit scope decisions for this task.
- **Explicitly authorized frontend touch, now including a breaking `/generate` contract change.** This task otherwise stays backend-only, but the user explicitly authorized editing `VitroFit_web` where needed: `src/api/dietPlan.js` (`pollDietWorkflow()`, the start-then-poll client, plus `refineDietPlan()`), `DietPlan.jsx` (drives the poll loops for both generate and refine, tracks live/error/refine step state), and `DietPlanResult.jsx` (renders live per-agent progress while generating, a plain-language "What happened" breakdown on failure, and the free-text refine box on the result screen). `/generate`'s response shape changed from the full plan to `{workflowId, status, plan}` — no longer purely additive, by design, to support live progress.
- **Refine only applies to the freshly generated, not-yet-confirmed plan** (the `result` screen), not an already-saved plan (the `view` screen) — saved plans don't carry a `workflowId` today (they come from `diet_plans`/`diet_plan_inputs`, not `diet_workflows`). Extending refine to saved plans would mean either keeping the originating `DietWorkflow` row linked past confirmation or starting a fresh one from the saved plan's stored data - a reasonable follow-up, not implemented here.
