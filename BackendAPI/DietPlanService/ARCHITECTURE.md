# Diet Plan Agent — Architecture Deep Dive

This is the detailed companion to [`AGENT.md`](AGENT.md) (which is the 1-page, presentation-ready summary). Where `AGENT.md` tells the story in 60 seconds, this document explains the actual mechanics: every agent's exact contract, what the coordinator does step by step, why each threshold is what it is, and how the frontend turns all of it into what the user sees.

---

## 1. System Overview

```
┌─────────────────────────────┐        ┌──────────────────────────────────────────┐
│  VitroFit_web (React)        │        │  DietPlanService (FastAPI)                │
│                               │        │                                            │
│  DietPlan.jsx                │  HTTP  │  main.py                                  │
│  ├─ handleGenerate() ────────┼───────>│  POST /api/diet/generate                  │
│  ├─ pollWithPacedReveal() <──┼────────┤  GET  /api/diet/workflows/{id}            │
│  ├─ handleRefine() ──────────┼───────>│  POST /api/diet/workflows/{id}/refine     │
│  └─ handleConfirm() ─────────┼───────>│  POST /api/diet/confirm                   │
│                               │        │         │                                  │
│  DietPlanResult.jsx           │        │         v                                  │
│  ├─ LiveStepCard (progress)  │        │  workflow.py (the coordinator)            │
│  ├─ PlanDetails (the plan)   │        │  ├─ create_workflow()  — persist + return │
│  └─ RefineBox (edit input)   │        │  ├─ execute_workflow() — background task  │
└───────────────────────────────┘        │  └─ execute_refine()   — background task  │
                                          │         │                                  │
                                          │         v                                  │
                                          │  agents.py (the 3 agents)                 │
                                          │  ├─ NutritionAnalystAgent                 │
                                          │  ├─ MealGeneratorAgent                    │
                                          │  └─ SafetyValidatorAgent                  │
                                          │         │                                  │
                                          │         v                                  │
                                          │  calculator.py │ meal_agent.py │ validators.py
                                          │  (pure math)   │ (NVIDIA NIM)  │ (rule engine)
                                          │                                            │
                                          │  db.py — PostgreSQL: diet_workflows,       │
                                          │          diet_plans, diet_plan_inputs      │
                                          └──────────────────────────────────────────┘
```

The core design decision: **the LLM never computes numbers.** `calculator.py` (deterministic Mifflin-St Jeor formula) is the only source of calorie/macro targets, for the entire life of a request. The Meal Generator's LLM call only chooses which foods to list against a target it's handed — it cannot override it, and everything it produces is re-checked by a separate, non-AI rule engine (`validators.py`) before it's ever shown as a finished plan.

The second core decision: **`/generate` doesn't block.** It used to run the whole workflow synchronously inside the HTTP request. Measured against the real NVIDIA endpoint, a single meal-generation call can legitimately take 65–120 seconds, and the workflow may need up to three such calls. Blocking the request for that long is bad UX and risks proxy/browser timeouts, so `/generate` now returns a `workflowId` in well under a second, the actual work runs as a detached background `asyncio` task, and the frontend polls for live progress.

---

## 2. The Three Agents

Each agent is a small Python class in `agents.py`: a `name`, an `allowed_tools` list that `workflow.call_tool()` enforces (an agent literally cannot invoke a tool not in this list — `call_tool()` refuses and logs it), a Pydantic input model, a Pydantic output model, and one `async def run(...)` method.

### 2.1 Nutrition Analyst Agent — domain analysis, no AI

**Allowed tools:** `calculate_targets`, `assess_risk`, `lookup_budget`

**Input** (`NutritionAnalystInput`):
```python
prefs: dict   # the full DietPlanPreferences payload from the form
```

**Output** (`NutritionAnalystOutput`):
```python
targets: dict                    # {"totalCalories": int, "macros": {"protein": int, "carbs": int, "fat": int}}
risk_level: Literal["low", "medium", "high"]
risk_flags: list[RiskFlag]       # [{"code": str, "message": str}, ...]
budget_context: dict             # resolved budget tier: label, guidance text, reference prices
```

**What `run()` actually does**, in order:

1. Calls `calculator.calculate_targets(gender, age, height_cm, weight_kg, activity_level, goal)`. This is the Mifflin-St Jeor BMR formula (`10×weight + 6.25×height - 5×age + 5` for men, `-161` instead of `+5` for women), multiplied by an activity factor (`sedentary` 1.2 → `active` 1.725) and a goal multiplier (`weight loss` 0.85, `muscle gain` 1.12, `endurance` 1.05, `maintenance` unchanged). Macros are then split from that calorie total by a fixed grams-per-100-kcal table that varies by goal (e.g. weight loss: 12g protein / 9g carbs / 3g fat per 100 kcal).
2. Calls the internal `_assess_risk(prefs, targets)` — see below.
3. Calls `budget_reference.resolve_tier(budgetTier, budgetCustomAmount)` — a static lookup table of three tiers (low/medium/high), each with a guidance sentence and ~8 reference-priced grocery items in LKR, used to ground the Meal Generator's prompt in what's actually affordable. A `custom` tier snaps to the nearest bucket by threshold (<2000, ≤4000, >4000 LKR/day).

**`_assess_risk()` — the exact threshold ladder:**

```python
maintenance = calculate_targets(..., goal="maintenance")["totalCalories"]  # same profile, "maintenance" goal
deficit_ratio = (maintenance - calories) / maintenance

flags:
  UNDER_18                    if age < 18
  MEDICAL_CONDITIONS_PRESENT  if any medicalConditions declared
  BELOW_SAFE_FLOOR            if calories < 1200
  STEEP_DEFICIT               if deficit_ratio >= 0.25   ("steep deficit" = 25%+ below maintenance)

risk_level:
  "high"    if calories < 1200  OR  (medical conditions present AND age < 18)
  "medium"  if medical conditions present  OR  deficit_ratio >= 0.25  OR  age < 18
  "low"     otherwise
```

This is the only place risk is computed — nowhere else in the codebase re-derives it, so the API response's `riskLevel` field and the frontend's risk explanation are always reading the same source of truth. `requiresApproval` (surfaced to the frontend) is `risk_level == "high"` only — `"medium"` is recorded but does not block anything, a deliberate choice so a mild medical condition or a slightly steep deficit doesn't force every such user through a trainer.

### 2.2 Meal Generator Agent — the only agent allowed to call the LLM

**Allowed tools:** `generate_meals`, `refine_meals`

**Input** (`MealGeneratorInput`):
```python
targets: dict
prefs: dict
corrective_note: str | None = None    # set by the coordinator on a revise-retry
current_meals: list[dict] | None = None   # set together with `instruction` to request an edit
instruction: str | None = None            # instead of a fresh generation
```

**Output** (`MealGeneratorOutput`):
```python
meals: list[Meal]          # [{"type": str, "label": str, "items": [{"name", "portion", "calories", "macros": {...}}]}]
withinTolerance: bool
error: str | None = None
```

`run()` branches on whether `current_meals`/`instruction` are set: if so, it calls `meal_agent.refine_meals(...)` (a targeted edit); otherwise `meal_agent.generate_meals(...)` (a fresh draft), threading `corrective_note` into the prefs dict under the key `_corrective_note` first if present.

**How the actual LLM call works** (`meal_agent.py`, using `openai.AsyncOpenAI` pointed at NVIDIA's OpenAI-compatible endpoint, `https://integrate.api.nvidia.com/v1`):

- Models: `NVIDIA_MODEL_PRIMARY` (default `meta/llama-3.2-11b-vision-instruct`) then `NVIDIA_MODEL_FALLBACK` (defaults to the same model) if the first attempt returns nothing.
- Per-attempt timeout: `_CALL_TIMEOUT_SECONDS = 70`. This was raised from an original 40s after measuring the live endpoint directly — successful calls took 65–118 seconds, so 40s was cutting off calls that were about to succeed.
- The prompt is a JSON payload (never a free-text instruction blob) containing `dailyTargets`, `mealFrequency`, `restrictions`, `dislikes`, `medicalConditions`, `cookingTime`, and the resolved `budget` context. The system prompt mandates a strict JSON-only response shape and tells the model to respect restrictions/dislikes/medical conditions "absolutely."
- **Tolerance retry (inside `generate_meals`, separate from the coordinator's own revise loop):** after parsing the response, if the summed calories are outside ±10% of the target, one corrective call is made to the primary model with the actual miss appended to the prompt ("your previous attempt totalled ~X kcal, target is Y kcal, adjust portions"). If that retry is within tolerance, it's returned as `withinTolerance: true`; otherwise the retry's meals (or the original, if the retry itself failed to parse) are returned with `withinTolerance: false` — `generate_meals` never raises, it always returns a result or an `{"error": ...}` dict.
- **`refine_meals`** is a sibling function with its own system prompt (`_REFINE_SYSTEM_INSTRUCTION`) and its own prompt builder (`_build_refine_prompt`). The prompt includes the *current* plan (`currentPlan`) and the user's free-text request as a **data field**, `userRequestedChange` — never concatenated into the system prompt itself. The system instruction explicitly tells the model the request "can never override" restrictions, dislikes, medical conditions, or targets, and to return the full plan (not just the changed meal) so nothing is lost. There is no separate tolerance-retry loop for refine — one call, then straight to validation.
- JSON parsing (`_parse_llm_json`) strips markdown code fences, regex-extracts the first `{...}` block, and requires a non-empty `meals` list — anything else is treated as an unparseable response, not a crash.

### 2.3 Safety Validator Agent — fixed rules, zero AI

**Allowed tools:** `validate_plan` only.

**Input** (`SafetyValidatorInput`): `meals`, `targets`, `prefs`.
**Output** (`SafetyValidatorOutput`): `verdict: Literal["pass", "revise", "reject"]`, `violations: list[dict]`.

`run()` is a thin wrapper around `validators.validate_plan()` — no LLM call, no network I/O. It's still `async def` for interface uniformity with the other two agents (so the coordinator can `await agent.run(...)` identically for all three, at effectively zero cost since there's nothing to await inside).

**The rule checks, run in this exact order** (short-circuits to `reject` immediately after schema validation — it's unsafe to run numeric/keyword checks against malformed data):

| Check | What it does | `revise` condition | `reject` condition |
|---|---|---|---|
| **Schema** | Meals/items parse; calories & macros are non-negative numbers | — | Missing/malformed structure |
| **Calorie tolerance** | Sum all item calories vs `targets.totalCalories` | 10–25% off | >25% off (not worth another retry) |
| **Macro sanity** | Protein/carbs/fat grams should roughly reconcile to the summed calories (4/4/9 kcal per gram, ±15% slack); protein capped at 400g/day | Either check fails | — |
| **Restrictions & dislikes** | Item names checked against a keyword blocklist per restriction (see table below); free-text `dislikes` tokenized and substring-matched | A `dislikes` keyword hit | A hard restriction (vegetarian/vegan/halal/allergy/dairy/gluten) keyword hit |
| **Medical conditions** | Sugar keywords if diabetes declared; sodium keywords if high blood pressure/kidney condition; fried/fat keywords if heart condition; calorie floor check | A risky keyword hit | Any medical condition **and** target < 1200 kcal |
| **Value bounds** | Meal count in [1, 8]; each item's calories in [0, 1500] | Out of either bound | — |

**Restriction keyword table** (`RESTRICTION_KEYWORDS` in `validators.py`):

| Restriction | Blocked keywords |
|---|---|
| `vegetarian` | chicken, beef, pork, fish, shrimp, prawn, bacon, ham, meat, mutton, goat, turkey, salami, sausage, duck |
| `vegan` | (all of vegetarian's) + egg, milk, cheese, yoghurt, honey, butter, ghee, curd, cream |
| `halal` | pork, bacon, ham, alcohol, wine, beer |
| `dairy-free` / `lactose-intolerant` | milk, cheese, yoghurt, butter, ghee, curd, cream |
| `gluten-free` | wheat, bread, pasta, noodle, flour, barley, rye, roti, naan |
| `peanut allergy` | peanut, groundnut |

Vegetarian/vegan/halal/allergy/dairy/gluten hits are **reject**-tier (a religious or safety rule, never silently patched); a free-text `dislikes` match is **revise**-tier (a soft preference, worth one more attempt).

**Final verdict:** `reject` if any violation is reject-severity; else `revise` if any violations exist at all; else `pass`.

---

## 3. The Coordinator (`workflow.py`)

### 3.1 `build_plan()`

A static, four-step plan (not dynamic re-planning) — this is deliberately simple and explainable: Nutrition Analyst (`calculate_targets`, `assess_risk`) → Meal Generator (`generate_meals`) → Safety Validator (`validate_plan`). If medical conditions are present, a `medical_review` note is appended to step 4's description. This plan is persisted immediately and returned to the client so the UI can show it before any step has actually run.

### 3.2 `call_tool()` — the dispatcher every agent call goes through

```python
async def call_tool(agent, tool, payload, events, step) -> {"ok": bool, "data": dict|None, "error": str|None}
```

1. **Allow-list check first.** If `tool not in agent.allowed_tools`, the call is refused immediately — no timeout, no execution — and logged as a failed event. This is the actual enforcement mechanism behind "agents can only use their own tools," not just a naming convention.
2. **Per-tool timeout.** `generate_meals` and `refine_meals` get 220 seconds (sized to `meal_agent`'s own worst case: three attempts × 70s = 210s, plus margin). Every other tool (pure Python, no I/O) gets a 10-second default — a safety net, not a real constraint.
3. **Event logging.** Every call — success, timeout, or exception — appends one entry to the workflow's `events` list: `{ts, step, agent, tool, ok, error, duration_ms}`. Raw prompts, full payloads, and secrets are never logged, only the fact that a call happened and how it went.

### 3.3 `create_workflow()` + `execute_workflow()` — the split that enables live progress

- `create_workflow()` is synchronous and fast: builds the plan, inserts a `DietWorkflow` row (`status="running"`), commits, returns. This is what `POST /api/diet/generate` calls directly, so the HTTP response can return the `workflowId` immediately.
- `execute_workflow()` is scheduled via `asyncio.create_task()` right after — it opens its **own** database session (`SessionLocal()`, not the request's, since that session closes when the request returns) and runs `_run_steps()`. Because nothing `await`s this task directly in production, it wraps everything in a `try/except` that guarantees the row ends in a terminal status even on a genuinely unexpected exception — otherwise the row would be stuck in `"running"` forever with no one left to report the failure.
- `run_workflow()` is a synchronous convenience wrapper (`create_workflow()` then `await execute_workflow()` then refresh) — used by tests and anything that wants to await full completion in one call, rather than the production split.

`main.py` holds a module-level `set()` of these background tasks (`_background_tasks`) purely so Python's garbage collector doesn't reap a task that nothing else references — a `task.add_done_callback()` removes it from the set once it finishes.

### 3.4 `_run_steps()` — the actual execution, step by step

1. **Step 1+2 (Nutrition Analyst).** One `call_tool()` call computes both targets and risk together (the agent's `run()` does both internally). On failure, the workflow ends `"failed"`. On success, `targets` and `risk_level` are written to the row, and **two** `completed_steps` entries are appended (step 1 for the calculation, step 2 for the risk assessment — including the full `riskFlags` list, not just the label, so the frontend can explain *why*).
2. **Deadline check.** After every step, `time.monotonic()` is compared against a deadline set at `_OVERALL_TIME_BUDGET_SECONDS` (230s) from the start. If exceeded, the workflow ends `"failed"` with a message naming the actual configured budget.
3. **Step 3 (Meal Generator).** One `generate_meals` call. On failure or an `"error"` in the result, `"failed"`.
4. **Step 4 (Safety Validator) — the revise loop.** This is a `while True` loop:
   - Validate the current meals. Persist `validation_results` and a rich `completed_steps` entry: `verdict`, `attemptCalories`, `targetCalories`, `diffPct`, and up to 5 `violations` — this is what lets the frontend show the actual calorie miss and the specific reason, not just a pass/fail flag.
   - **`pass`** → break out of the loop, proceed to the success block.
   - **`reject`** → `status = "rejected"` immediately, `final_outcome` carries the violations, **no retry is attempted**. This is the one guaranteed hard stop.
   - **`revise`** → increment `retry_count`. If it now exceeds `_MAX_REVISE_RETRIES` (which is `1`, meaning 2 total meal-generation attempts: the original plus one retry), **soft-degrade**: the workflow still ends `"completed"`, carrying the closest attempt's meals with `withinTolerance: false` and a `note` explaining why, rather than ending in `"failed"` with nothing to show. This deliberately matches how the service behaved *before* this workflow existed — the original `/generate` always returned some plan, flagging a mismatch with a warning banner instead of blocking the user outright. If retries remain, a corrective note is built from the specific `revise`-severity violations (`_summarize_violations`) and threaded into a fresh `generate_meals` call via `corrective_note`, which `meal_agent._build_prompt` surfaces to the LLM as a `previousAttemptFeedback` field — so the retry is actually informed, not a blind repeat.
5. **Success.** `status = "completed"`, `final_outcome` carries the final totals and whether the last validation was a clean `pass`. `approval_status` is set to `"pending"` if `risk_level == "high"`, else `"auto_approved"`.

### 3.5 `execute_refine()` — applying an edit without re-running the whole pipeline

This only touches the Meal Generator and Safety Validator — the Nutrition Analyst doesn't run again, because the targets haven't changed.

1. Snapshot the current `meals` before doing anything (`original_meals`), clear any stale `wf.error`.
2. Call `refine_meals` via `call_tool` (tool name `refine_meals`, tagged `"refine": True` in its `completed_steps` entry so the frontend can distinguish it from the original generation's steps). On failure, revert: `wf.error` is set to a plain-language reason, `status` goes back to `"completed"` (not `"failed"` — the *previous* plan is still perfectly valid, only the requested edit didn't go through).
3. **The edit is always re-validated**, exactly like a fresh generation — this is the actual safety guarantee, not the LLM's system prompt (which is only the first, advisory layer). If the validator's verdict is `reject`, the edit is discarded and `wf.meals` is left untouched; the error message explains which rule the edit would have broken.
4. If `pass` or `revise` (a tolerance nuance, not a safety issue), the edit is applied — same soft-degrade philosophy as the main flow: don't block a user's requested change over a calorie-tolerance detail, only over an actual safety rule.
5. Any unhandled exception is caught at the top level and treated the same as a failed edit: the plan is left as it was, `status` returns to `"completed"`, and `wf.error` explains what happened — a refine attempt can never leave the workflow row stuck or the plan corrupted.

---

## 4. Data Model

One new table, `diet_workflows` (`workflow_models.py`), added via the existing `Base.metadata.create_all` pattern — no migration tooling, no `ALTER` on the pre-existing `diet_plan_inputs`/`diet_plans` tables.

| Column | Type | Purpose |
|---|---|---|
| `id` | UUID | Primary key, the `workflowId` the frontend polls |
| `user_id` | Integer | Owner (from the JWT `sub` claim) |
| `objective` | String | Always `"generate_diet_plan"` today |
| `status` | String | `running` → `completed` \| `failed` \| `rejected` |
| `plan` | JSON | The static 4-step plan from `build_plan()` |
| `completed_steps` | JSON | Grows in real time — this is what the frontend polls to show live progress |
| `inputs` | JSON | The submitted preferences (`DietPlanPreferences`, snapshotted) |
| `targets` | JSON | `{totalCalories, macros}` once step 1 finishes |
| `meals` | JSON | The current meal plan (overwritten by each retry/refine) |
| `validation_results` | JSON | The *last* validator verdict + violations |
| `events` | JSON | The full tool-call audit trace (agent, tool, timing, ok/error) |
| `risk_level` | String | `low` \| `medium` \| `high` |
| `approval_status` | String | `pending` \| `auto_approved` \| `approved` \| `rejected` |
| `approved_by`, `approval_note` | Integer, String | Set by a Trainer/Admin decision |
| `final_outcome` | JSON | Terminal-state summary (totals, `withinTolerance`, or a rejection/failure reason) |
| `error` | Text | Human-readable reason for `failed`, or a reverted-refine explanation while still `completed` |
| `retry_count` | Integer | How many revise-retries have happened |
| `plan_id` | Integer | Loose (no FK) link to `diet_plans.id`, set once the workflow's plan is confirmed/saved |

`diet_plans` and `diet_plan_inputs` (pre-existing, unchanged) remain the actual persisted-plan tables — a `DietWorkflow` row is the *process record* of getting there, not a replacement for them. `POST /api/diet/confirm`, given a `workflowId`, copies the workflow's own validated `targets`/`meals` into those tables (ignoring anything the client sent for those fields) and links `plan_id` back.

---

## 5. Security

- **Identity.** `auth.py` verifies the same JWTs `VitroFit.API` issues (HS256), reading the signing key/issuer/audience directly from `VitroFit.API/appsettings.json` at import time (with optional `JWT_SECRET`/`JWT_ISSUER`/`JWT_AUDIENCE` env-var overrides, used by the test suite so it never touches the real secret). `get_current_user_id` extracts just the numeric `sub` claim for ownership checks; `get_current_user_claims` (added for this workflow) exposes the full claim set for role checks.
- **Authorization.** `security.require_roles(*roles)` is a FastAPI dependency factory built on `get_current_user_claims`. It checks the role claim under both a short `"role"` key and .NET's long `ClaimTypes.Role` URI (confirmed against `VitroFit.API/Services/TokenService.cs`), since that's how the issuing service actually serializes it. Approval endpoints require `Trainer` or `Admin`; workflow detail/trace endpoints allow the owner **or** a Trainer/Admin.
- **Input validation.** `DietPlanPreferences`' string fields are all `Literal[...]` enums matching the exact values `DietPlan.jsx`/`DietPlanPreferenceForm.jsx` actually send (verified against the live frontend source, not assumed) — an unrecognized value is a 422, not a silent pass-through. Free text (`dislikes`, the refine `instruction`) is stripped of control characters and length-capped (`_sanitize_free_text`) before it ever reaches a prompt.
- **Prompt-injection posture.** User-supplied text is always sent to the LLM as a JSON *data* field (`dailyTargets`/`userRequestedChange`/etc.), never concatenated into the system prompt. The system prompt for `refine_meals` explicitly tells the model the user's request cannot override restrictions/medical conditions/targets. This is treated as advisory, not a guarantee — the actual guarantee is that the Safety Validator re-checks every result regardless of what the LLM did.
- **Secrets.** Never logged — `call_tool()`'s event trace records only agent/tool/timing/ok-or-error, never prompts or payloads. The NVIDIA API key and JWT secret are read from environment/config, never hardcoded.
- **Reliability.** Every LLM-touching tool has an explicit timeout; the revise loop has a hard retry cap (`_MAX_REVISE_RETRIES = 1`); the whole workflow has an overall deadline (`_OVERALL_TIME_BUDGET_SECONDS = 230`); and every background task (`execute_workflow`, `execute_refine`) has a top-level exception handler that guarantees a terminal status — a "safe failure" is always the worst case, never a stuck or corrupted row.

---

## 6. Frontend Architecture

### 6.1 The polling primitives (`src/api/dietPlan.js`)

- `generateDietPlan(prefs)` / `refineDietPlan(workflowId, instruction)` — POST, return immediately with `{workflowId, status: "running"}`.
- `getDietWorkflow(workflowId)` — one GET of the current state.
- `pollDietWorkflow(workflowId, {onProgress, intervalMs=2000, timeoutMs=240000})` — polls every 2s, calling `onProgress` with the raw detail each time, until a terminal status. On `"completed"`, resolves with a plan-shaped object (`totalCalories`, `macros`, `meals`, `completedSteps`, etc. — flattened from the workflow detail's `targets`). On `"failed"`/`"rejected"`, throws an `Error` carrying `completedSteps` as a property, so the catch site still has the full trace to show.

### 6.2 Paced reveal (`DietPlan.jsx`'s `pollWithPacedReveal()`)

A deliberate UX layer on top of `pollDietWorkflow`: even if the backend finishes in a few seconds, the UI still reveals one `completed_steps` entry at a time on a fixed delay (`STEP_REVEAL_DELAY_MS = 4200`ms), and **does not** flip to the result/error screen until every step up to the final result has actually been shown. Mechanically, it runs a reveal loop concurrently with the real polling: the loop checks how many steps are known vs. how many have been revealed, sleeps, reveals the next one, and only exits once the workflow is marked done *and* every known step has been shown.

### 6.3 Live progress cards (`DietPlanResult.jsx`)

`describeLiveStep(step, detail, allSteps)` turns one raw `completed_steps` entry into `{icon, label, variant, points}` — a handful of short, plan-focused bullet points (target numbers, risk level and why, drafted meal names, calorie-vs-target and verdict), deliberately **not** a description of what the agent is allowed to do. `variant` (`default`/`pass`/`revise`/`reject`) drives the card's color (theme accent / accent / amber / red). One correctness detail: since `detail.meals` only ever holds the *latest* attempt, a Meal Generator step earlier in the list than the most recent one is not shown with meal names (it would be wrong) — only the most recent Meal Generator entry gets that detail.

**These cards persist.** Once generation finishes, `DietPlanResult.jsx`'s `result` state re-renders the same cards (filtered to `!step.refine`) above the plan itself, so they stay visible the entire time the plan is unconfirmed — they don't vanish the moment the plan is ready.

### 6.4 Refine box and highlight-on-edit

The refine box (`RefineBox`) intentionally does **not** show the same card breakdown while applying an edit — just a plain "Applying your change…" line. What it does show, once the edit lands, is a highlight: `DietPlan.jsx`'s `diffMealItems(prevMeals, nextMeals)` compares the *same position* (meal index, item index) before and after and returns the set of positions whose name changed. This is deliberately positional, not name-based — an earlier name-matching implementation broke when the LLM's replacement item happened to share a name with another item already in the same meal (verified against a real captured case). The changed item gets a highlighted border and a "Changed" badge (`.dp-meal-item-changed`) that persists until the plan is confirmed or a new one is generated.

### 6.5 Auto-scroll

A `contentRef` wraps the page's main content area; a `useEffect` keyed on the `phase` state (`'loading'`/`'result'`/`'error'`/`'view'`/etc.) calls `scrollIntoView({behavior: 'smooth', block: 'start'})` on every phase change (skipping the very first render). The preference form has its own, separate mechanism for the same idea at a finer grain: `DietPlanPreferenceForm.jsx` keeps a ref per validatable field, and on a failed submit scrolls to whichever invalid field appears first in the form's actual top-to-bottom layout — not just the top of the page — since a validation error a few fields up can otherwise render off-screen with no visible change on submit.

### 6.6 Phase state machine (`DietPlan.jsx`)

```
loading-plans → browse ⇄ view
              ↘ empty  ⇄ form → loading → result ⇄ (refine, in place)
                                        ↘ error → (edit or retry) → loading
```

`plan` (the current generated/edited plan object) and `changedItemKeys` (the refine highlight) are cleared whenever a new generation starts, a plan is confirmed, or the user starts over — so nothing stale leaks between one plan and the next.

---

## 7. Testing

26 tests across `tests/test_validators.py`, `test_agents.py`, `test_workflow.py`, `test_meal_agent.py`, and `test_main_endpoints.py` — the LLM is mocked at the `agents.generate_meals`/`agents.refine_meals` boundary (never the OpenAI client internals), so no real NVIDIA call happens in CI. Coverage includes: every validator verdict (pass/revise/reject) and the specific rule that produced it, tool-allowlist enforcement (a forbidden tool call is refused and logged), the full revise-then-pass and retry-exhausted-then-soft-degrade paths, the reject-short-circuits-immediately path, the corrective-note actually reaching the LLM prompt, role-gated approval (403 for a plain `User`, 200 for `Trainer`), a refine edit applying cleanly, and — importantly — a refine edit being *rejected and reverted* with the specific violation surfaced in the live trace (this test deliberately forces the mocked LLM to suggest a restricted ingredient, to prove the Safety Validator catches it even on a user-requested edit).

---

## 8. Where to Look for More

- [`AGENT.md`](AGENT.md) — the 1-page summary, the flow diagram, and the running list of tradeoffs/judgment calls made along the way (inline-vs-background execution, the 230s budget, the risk-approval threshold, and others) — that list is not duplicated here to avoid the two documents drifting out of sync.
- `workflow.py`, `agents.py`, `validators.py`, `meal_agent.py` — read in that order for the actual implementation behind everything above.
