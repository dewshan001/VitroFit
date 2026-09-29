# Diet Plan Agent — Multi-Agent Workflow

## How I explain it in 60 seconds

My Diet Planning workflow has three agents with different jobs. A small coordinator (`workflow.py`) builds a plan of steps and hands each one to the right agent. Each agent can use only its own approved tools — the Meal Generator is the only one allowed to call the LLM, and it can't touch the database. The Safety Validator checks the finished meals against fixed rules, not AI — calorie tolerance, allergy/restriction keywords, medical-condition sanity checks. If validation says "revise," the coordinator sends the specific problems back to the Meal Generator for another attempt (max 2 retries) before giving up safely. If a plan is classified high-impact — under a safe calorie floor, or a minor with a medical condition — it pauses and waits for a Trainer or Admin to approve it before it can be saved. Every step, tool call, retry, and decision is logged to a `diet_workflows` row, so the whole run is traceable end to end.

## Flow

```
Request -> Coordinator builds plan
   Step 1  Nutrition Analyst   -> targets + risk level          (tools: calculate_targets, assess_risk, lookup_budget)
   Step 2  Meal Generator      -> meals (LLM)                   (tool:  generate_meals)
   Step 3  Safety Validator    -> pass / revise / reject        (tool:  validate_plan, rules only)
              revise -> back to Meal Generator (max 2 retries) else safe failure
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

- **Inline 90s execution ceiling.** `run_workflow()` runs synchronously inside `POST /api/diet/generate`, so a single request can take close to the 90s overall budget (`generate_meals` alone gets up to 85s, since `meal_agent.py` internally may try two model calls plus one corrective retry, each up to 40s). A polling design (`/generate` returns `workflowId` immediately, client polls `/workflows/{id}`) would remove this ceiling but requires a frontend change, which is out of scope for this backend-only task.
- **`requiresApproval` triggers only on `risk_level == "high"`**, not `"medium"` — otherwise every under-18 user or anyone with a mild medical condition would always block on a trainer. This threshold is a judgment call and easy to tighten later (`agents._assess_risk`).
- **Known, pre-existing, deliberately untouched issues:** `db.py`'s hardcoded fallback DB password and the git-tracked `.env` file; the frontend's default API port (8002) doesn't match `.env.example`'s `PORT=8003`. Both were flagged and left alone per explicit scope decisions for this task.
