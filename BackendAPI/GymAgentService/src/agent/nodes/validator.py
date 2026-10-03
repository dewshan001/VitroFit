"""Validator / safety agent: deterministic gate before approval and publication.

No LLM and no tools. It is a pure function over the other agents' outputs so its
verdict is reproducible and testable.
"""

from src.models.contracts import ValidatorInput, Verdict
from src.utils.validators import validate


def run(inp: ValidatorInput) -> Verdict:
    return validate(inp)
