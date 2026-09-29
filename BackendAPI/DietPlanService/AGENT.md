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

- `POST /api/diet/generate` (JWT required) — runs the full workflow inline and returns `{totalCalories, macros, meals, withinTolerance, workflowId, status, riskLevel, plan, requiresApproval}`. The first four fields are unchanged from before this workflow existed; the rest are additive.
- `GET /api/diet/workflows/{workflowId}` — full detail (owner, or Trainer/Admin).
- `GET /api/diet/workflows/{workflowId}/trace` — ordered `events` + `completedSteps`, showing exactly which agent ran which tool, when, and whether it succeeded.
- `GET /api/diet/approvals/pending`, `POST /api/diet/workflows/{id}/approve`, `POST /api/diet/workflows/{id}/reject` — Trainer/Admin only.
- `POST /api/diet/confirm` accepts an optional `workflowId`; when given, it persists the workflow's own stored, validated data (ignoring anything the client sends for those fields) rather than trusting client-submitted plan data.

Status values: `running` → `completed` | `failed` | `rejected`. Approval values: `pending` → `approved` | `rejected`, or `auto_approved` for standard-risk plans.

## Known tradeoffs / judgment calls

- **Inline execution ceiling (230s).** `run_workflow()` runs synchronously inside `POST /api/diet/generate`, so a single request can take close to the 230s overall budget. This was raised from an initial 90s default after measuring the live NVIDIA endpoint directly: a single `meal_agent.generate_meals()` call took 65-118s on real, successful runs. `meal_agent._CALL_TIMEOUT_SECONDS` was raised from 40s to 70s per model attempt to match (it may need up to three attempts - primary, fallback, and one tolerance-correction retry - so 210s worst case). A polling design (`/generate` returns `workflowId` immediately, client polls `/workflows/{id}`) would remove the need for a long inline ceiling entirely, but requires a frontend change, out of scope for this backend-only task. If the NVIDIA model response time improves (e.g. switching `NVIDIA_MODEL_PRIMARY` to a smaller/faster model), these constants in `meal_agent.py` and `workflow.py` can be lowered back down.
- **`requiresApproval` triggers only on `risk_level == "high"`**, not `"medium"` — otherwise every under-18 user or anyone with a mild medical condition would always block on a trainer. This threshold is a judgment call and easy to tighten later (`agents._assess_risk`).
- **Known, pre-existing, deliberately untouched issues:** `db.py`'s hardcoded fallback DB password and the git-tracked `.env` file; the frontend's default API port (8002) doesn't match `.env.example`'s `PORT=8003`. Both were flagged and left alone per explicit scope decisions for this task.
- **Small, explicitly authorized frontend touch.** This task otherwise stays backend-only, but three `VitroFit_web` files were edited with the user's explicit go-ahead: `src/api/dietPlan.js` (carries the new `completedSteps` trace through on a failed `/generate` call), `DietPlan.jsx` (passes it to the result view), and `DietPlanResult.jsx` (renders a "What happened" per-attempt breakdown on the error screen, and cycles the loading state through the three real agent names). No existing request/response contract field was removed, only added to.
