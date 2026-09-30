"""Agent evaluation: golden cases for the gym workflow, checked by deterministic, rule-based assertions.

Nothing here uses an LLM as a judge. Each case scripts the model and the tools, runs the real graph,
runner, store and validator, and compares what happened with what the design says must happen.
"""
