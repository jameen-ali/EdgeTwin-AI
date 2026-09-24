# rules.md — EdgeTwin AI Engineering Rulebook (permanent)

These rules bind every contributor, human or AI. If a task conflicts with a rule, stop and raise it in `memory.md` instead of working around it.

## A. Honesty and scope
1. Do not invent functionality, citations, datasets, benchmarks, or results. Every research claim carries a source or is labelled **[ASSUMPTION]**.
2. Label everything: **[FACT]** (sourced), **[DECISION]**, **[PROPOSED]** (our contribution), **[ASSUMPTION]**.
3. Never present synthetic or simulated data as real industrial data. Simulated telemetry carries `provenance: "SIMULATED"` end to end and is labelled in the UI.
4. Never claim a feature is done until it is implemented **and** its acceptance tests pass. Status in `tasks.md` must match reality.
5. Novelty is described as "proposed system contribution". No "first in the world" claims without a reliable source.
6. Maintenance thresholds/recommendations are **system recommendations**, not industry safety standards. Never imply compliance with ISO or any standard unless verified.
7. Explanations show statistical association, never causation.

## B. Workflow
8. One task at a time: explain purpose → list files → implement only that task → test → report → update `memory.md` → update `tasks.md` status.
9. Do not modify unrelated files. Do not delete or overwrite working code, notebooks, or data without explicit approval. Raw data in `data/raw/` is immutable.
10. Do not introduce a dependency without a written justification in `memory.md` (what it does, why the stdlib/existing tool is insufficient).
11. Prefer the simpler design when it gives the same engineering value. No infrastructure that has no purpose in the demo or evaluation.
12. Document each major architectural decision (context, options, choice, consequences) in `memory.md`.

## C. Code quality
13. Production-quality code: typed (Python type hints, TypeScript strict), linted, formatted (ruff/black, eslint/prettier).
14. Validate all external input (MQTT, HTTP, files) at the boundary with explicit schemas. Handle errors explicitly; no bare `except`, no silent failures, no crashing on malformed messages.
15. Business logic lives in pure, unit-testable functions/services. Routers, MQTT handlers, and UI components stay thin.
16. Frontend and backend stay separate: the UI never computes health/risk; it renders API/twin state.
17. Reuse: feature engineering is **one shared module** used by training and serving (prevents train/serve skew). Do not copy logic between firmware and backend without a shared spec + contract test.
18. Maintain backward compatibility of the telemetry schema and REST API; breaking changes require a version bump (`v1` → `v2`) and a `memory.md` entry.

## D. ML rules
19. Reproducibility: fixed seeds, pinned dependencies, data hash (DVC), git commit, and params logged to MLflow for every run.
20. No leakage: `Failure_Type`, IDs, timestamps, batch codes, checksum flags are never features. Split **before** any fitted preprocessing; fitted preprocessing lives inside the pipeline. A test enforces the forbidden-column list.
21. Report Precision, Recall, F1, PR-AUC, ROC-AUC, confusion matrix; never accuracy alone. Select models on validation; touch the test set once per experiment round and record it.
22. Every registered model has a model card (data, metrics, limits, intended use). Promotion to `champion` requires the gate defined in `mlops/`.
23. Track model version on every prediction. Missing sensor values are `null`/NaN, never imputed as 0.

## E. Security
24. Never hardcode or commit secrets (API keys, passwords, tokens, DB or MQTT credentials). Use environment variables; commit `.env.example` only. Rotate any credential that ever appears in a public place (including public Wokwi projects).
25. TLS + authentication on MQTT; least-privilege credentials; validate `machine_id` against topic and payload.
26. Enforce role checks server-side. Rate-limit auth and command endpoints. Log security events without logging secrets.
27. Dependencies are pinned; CI runs a vulnerability check.

## F. Testing and docs
28. Tests for all important logic: unit (health engine, validators, features), API, ML (leakage guard, metric sanity, determinism), integration (ingest→DB), contract (telemetry schema), and the end-to-end scenario.
29. Docs updated in the same change as the code. README must let a stranger run the stack.
30. `memory.md` is updated whenever a decision, bug, fix, limitation, dependency, API, or DB change occurs.

## G. Definition of done (any task)
Code merged on a branch with passing CI · tests added · docs/memory updated · acceptance criteria demonstrably met · status set in `tasks.md`.
