# Local Codex Policy for select-ai-apex

This file supplements the global `~/.codex/AGENTS.md`.

Keep this file repo-specific. Do not duplicate universal rules that already live in the global policy.

## Project Identity

- Repo root: the Git repository containing this file.
- Purpose: Deploy Select AI and an APEX application on Autonomous Database.
- Technical audience: OCI database, APEX, and platform engineers.
- Primary surfaces: Python installer, APEX exports, demo data, `terraform/`, and Deploy Studio hook.

## Repo Operating Defaults

- Preferred validation commands: `./scripts/check-project.ps1`; Terraform fmt/init/validate in `terraform/`.
- Preferred search and inspection tools: `semble search`, then literal `rg` for exhaustive references.
- Default runtime or environment assumptions: Python 3.11, Oracle wallet connectivity, OCI Resource Manager.

## Local Validation Policy

- Required checks beyond global Graphify and Sentrux: Python unit tests, Deploy Studio hook tests, and Terraform validation.
- Safe shortcuts for docs-only work:
- Release, deploy, or approval gates:

## Repo-Specific Friction

- Sensitive paths or fragile areas: `outputs/`, `.oci/`, wallets, generated SQL, and post-apply temporary files.
- Credentials, external systems, or approval boundaries: Never commit OCI keys, wallet material, passwords, Terraform state, or generated secret reports.
- Noisy, slow, or expensive commands to avoid by default:

## Continuous Improvement Triggers

- Promote a repeated friction to this local file after 2 recurrences in the same repo.
- Promote a repeated manual sequence to a script or skill after 3 recurrences or when it is safety-critical.
- Promote a rule to the global policy only when it is cross-repo or clearly universal.
- Review `.codex/improvement-log.md` before large tasks and record only meaningful signal after non-trivial work.

## Future Delegation Hooks

- Candidate explorer roles:
- Candidate reviewer roles:
- Candidate repo-specific skills or MCPs:
