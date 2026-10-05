"""Fault-injection check: does the test suite notice when a safeguard is broken?

Each entry below breaks one safeguard in the source (approval gate removed, injection guard disabled, tool
allow-list always true, ...), runs the whole test suite, and expects it to FAIL. The file is always restored
afterwards. A fault the suite does not notice is reported as SURVIVED and the script exits non-zero.

    python tests/evaluation/mutation_check.py          (from BackendAPI/DietPlanService; takes about two minutes)

It edits files in src/ while it runs, so do not edit them at the same time.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(ROOT)
PY = sys.executable

MUTATIONS = [
    ("approval gate removed (confirm)", "src/api/routes.py", "        blocked = _approval_block_message(wf)\n        if blocked:", "        blocked = None\n        if blocked:"),
    ("legacy high-risk gate removed", "src/api/routes.py", '    if risk_level == "high":\n        raise HTTPException(\n            status_code=409,', '    if False:\n        raise HTTPException(\n            status_code=409,'),
    ("legacy validation removed", "src/api/routes.py", '    if result["verdict"] == "reject":\n        raise HTTPException(status_code=422, detail=_violations_to_message', '    if False:\n        raise HTTPException(status_code=422, detail=_violations_to_message'),
    ("decision allowed on any state", "src/api/routes.py", '    if wf.status != "completed" or wf.approval_status != "pending":', '    if False:'),
    ("atomic claim ignored", "src/api/routes.py", "    if not claimed:", "    if False:"),
    ("injection guard never blocks (dislikes)", "src/api/routes.py", "    if guarded.blocked:", "    if False:"),
    ("approval reset after edit removed", "src/agent/workflow.py", 'if wf.risk_level == "high" and wf.approval_status in ("approved", "auto_approved"):', "if False:"),
    ("tool allow-list always true", "src/tools/tool_registry.py", "    if tool not in TOOL_PERMISSIONS.get(agent_name, ()):\n        return False", "    if False:\n        return False"),
    ("plan narrowing ignored", "src/tools/tool_registry.py", "    return plan_allowed is None or tool in plan_allowed", "    return True"),
    ("output safety check removed", "src/utils/validators.py", "    violations += _check_output_safety(meals)\n", ""),
    ("unsafe output returned after retries", "src/agent/workflow.py", "            if _has_unsafe_output(validation[\"violations\"]):\n                # Never", "            if False:\n                # Never"),
    ("restriction check removed", "src/utils/validators.py", "    violations += _check_restrictions_and_dislikes(meals, prefs)\n", ""),
    ("calorie tolerance check removed", "src/utils/validators.py", "    violations += _check_calorie_tolerance(totals, targets)\n", ""),
    ("time budget ignored", "src/agent/workflow.py", "        return time.monotonic() > deadline", "        return False"),
    ("startup recovery no-op", "src/agent/store.py", "        recovered += 1\n    if recovered:", "        pass\n    if recovered:"),
    ("concurrency cap ignored", "src/agent/runner.py", "semaphore = _slots[loop] = asyncio.Semaphore(MAX_CONCURRENT_WORKFLOWS)", "semaphore = _slots[loop] = asyncio.Semaphore(1000)"),
    ("audit mirror removed", "src/agent/store.py", "            session.add(DietWorkflowStep(", "            continue\n            session.add(DietWorkflowStep("),
    ("service key not checked", "src/utils/security.py", "    if not x_diet_agent_key or not hmac.compare_digest(", "    if False and not hmac.compare_digest("),
    ("server targets not used on legacy path", "src/api/routes.py", 'return None, targets["totalCalories"], targets["macros"], req.meals, req.withinTolerance', "return None, req.totalCalories, req.macros, req.meals, req.withinTolerance"),
    ("workflow data not trusted on confirm", "src/api/routes.py", "            wf.targets[\"totalCalories\"],\n            wf.targets[\"macros\"],\n            wf.meals,", "            req.totalCalories,\n            req.macros,\n            req.meals,"),
    ("prompt not escaped", "src/prompts/agent_prompts.py", "    return escape_for_fence(value) if isinstance(value, str) else value", "    return value"),
    ("refine unsafe-output check removed", "src/agent/workflow.py", ' or _has_unsafe_output(validation.get("violations") or [])', ""),
    ("safe-phrase exemption removed", "src/utils/validators.py", "    for phrase in exemptions.get(keyword, ()):\n        name = name.replace(phrase, \" \")\n", ""),
    ("retry limit raised", "src/agent/workflow.py", "_MAX_REVISE_RETRIES = 1", "_MAX_REVISE_RETRIES = 5"),
    ("violation target ignored", "src/agent/workflow.py", ' or not _generator_can_fix(validation["violations"]):', ":"),
]

survivors = []
for name, path, old, new in MUTATIONS:
    original = open(path, encoding="utf-8").read()
    if old not in original:
        print(f"SKIP  {name}: pattern not found")
        survivors.append((name, "pattern not found"))
        continue
    open(path, "w", encoding="utf-8").write(original.replace(old, new, 1))
    try:
        r = subprocess.run([PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"], capture_output=True, text=True, timeout=300,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        caught = r.returncode != 0
    finally:
        open(path, "w", encoding="utf-8").write(original)
    print(("CAUGHT   " if caught else "SURVIVED ") + name)
    if not caught:
        survivors.append((name, "survived"))
print("\nsurvivors:", survivors)
