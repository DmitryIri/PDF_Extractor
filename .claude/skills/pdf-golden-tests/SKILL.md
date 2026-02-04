---
name: pdf-golden-tests
description: Run canonical regression suite based on repo tests/ scripts (core) and optional E2E manual fixtures (if present).
---

# pdf-golden-tests

## Purpose
Provide a deterministic, low-token "quality gate" before declaring a task done:
- run the canonical regression tests (CORE suite)
- optionally run an E2E manual fixture (if available)

This skill exists to reduce back-and-forth and enforce evidence-based PASS/FAIL.

## Inputs
Optional:
- mode: core | e2e
- fixture selector for e2e (e.g., "Mg_2025-12")

Defaults:
- mode = core

## Source of Truth (repo facts)
CORE suite (must exist in repo):
- pytest tests/unit/ -v (or -q for compact output)
- bash tests/test_material_classification_golden.sh
- bash tests/test_output_builder.sh
- bash tests/test_output_validator_integration.sh
- python tests/test_output_validator_unit.py (only if used as a runner)

E2E suite (optional, only if script exists):
- bash tests/manual/test_full_pipeline_*.sh

## Procedure (deterministic)
1) Discover available suites by listing tests/ paths (no assumptions).
2) Run CORE suite always (unless explicitly asked otherwise).
3) If mode=e2e:
   - locate a matching tests/manual script for the selector.
   - run it, capturing PASS/FAIL evidence.
4) Output:
   - PASS/FAIL
   - exact failing command
   - minimal next commands to reveal diffs (sha256sum / diff)

## Output rules
- Never claim PASS without command output.
- Never invent fixture names or scripts.
- If required script is missing, print exact discovery commands and stop.

## Safety
- No destructive commands.
- No rewriting expected outputs unless explicitly requested.
