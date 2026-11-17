from __future__ import annotations

from pathlib import Path

from .models import RenderedPlan


def write_rendered_plan(rendered: RenderedPlan, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "01_admin_bootstrap.sql").write_text(rendered.admin_sql, encoding="utf-8")
    (output_dir / "02_select_ai_profile.sql").write_text(rendered.app_sql, encoding="utf-8")
    (output_dir / "03_apex_import_prelude.sql").write_text(rendered.apex_prelude_sql, encoding="utf-8")
    (output_dir / "04_apex_post_install.sql").write_text(rendered.apex_post_sql, encoding="utf-8")
    (output_dir / "executed-steps.sql").write_text(rendered.executed_steps_sql, encoding="utf-8")
    (output_dir / "deployment-report.md").write_text(rendered.report_markdown, encoding="utf-8")
    (output_dir / "secrets.json").write_text(rendered.secrets_json, encoding="utf-8")
