# Improvement Log - select-ai-apex

Use this file for evidence-backed harness improvements in this repo.

Keep entries short. Record real friction, recurring overhead, or meaningful improvements only.

## Promotion Thresholds

- 2 recurrences in this repo -> local `.codex/AGENTS.md` candidate
- 3 recurrences or safety-critical repetition -> script or skill candidate
- Cross-repo or clearly universal pattern -> global `~/.codex/AGENTS.md` candidate

## Entry Template

| Date | Task or Incident | Friction Observed | Evidence | Action Taken or Proposed | Promotion Target | Status |
| --- | --- | --- | --- | --- | --- | --- |
| YYYY-MM-DD |  |  |  |  | local AGENTS / script / skill / global AGENTS / none | captured |
| 2026-07-03 | Full unit-test run | `PYTHONPATH=installer` made `installer/secrets.py` shadow Python's standard-library `secrets` module. | `generate_oracle_password` failed with `AttributeError: module 'secrets' has no attribute 'choice'`. | Use `random.SystemRandom`, preserving cryptographic randomness without the module-name collision. | none | resolved |
