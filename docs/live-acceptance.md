# Live Acceptance Checklist

Use real OCI and Autonomous Database credentials only in a secure local environment.

- New Autonomous Database 26ai:
  - Run `select-ai-apex plan --mode new ... --db-version 26ai`.
  - Apply `terraform/`.
  - Decode the generated wallet and run `select-ai-apex install`.
  - Confirm the APEX app imports with supporting objects.
- New Autonomous Database 19c:
  - Repeat the flow with `--db-version 19c`.
  - Confirm optional vector grants are skipped rather than failing when unavailable.
- Existing Autonomous Database:
  - Run `select-ai-apex install --mode existing --wallet wallet.zip --admin-user ADMIN ...`.
  - Confirm `SELECT_AI_APP` is created or reused.
- Access expansion:
  - Grant `SELECT` on a new table to `SELECT_AI_APP`.
  - Re-run `select-ai-apex install` or `plan` followed by `02_select_ai_profile.sql`.
  - Confirm the profile can answer over the new table.
- APEX profile preference:
  - Sign in with the generated APEX user.
  - Confirm the `CLOUD_AI_PROFILE` preference points to `grok_reasoning`.
