# Select AI APEX Repository Instructions

- The Deploy Studio contract is `deploy-studio.json`; keep the Terraform package at `terraform/` for CLI compatibility.
- The repository-owned post-apply entrypoint is `deploy/hooks/post_apply.py`; it must use only the temporary file paths provided by Deploy Studio and must never put secrets in events or outputs.
- Never commit `.oci`, wallets, passwords, Terraform state, generated SQL, or `outputs/`.
- Keep infrastructure names derived from `deployment_suffix`; legacy name variables are compatibility overrides only.
- Before non-trivial changes run `./scripts/arch-preflight.ps1`; before completion run `./scripts/arch-postflight.ps1`.
- Run `./scripts/check-project.ps1` and Terraform `fmt -check`, `init -backend=false`, and `validate` before release.
