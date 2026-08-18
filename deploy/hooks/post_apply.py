from __future__ import annotations

import base64
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
from typing import Callable, Mapping, Sequence
from urllib.parse import quote, urlsplit, urlunsplit
import zipfile


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from installer.cli import main as installer_main  # noqa: E402
from installer import demo_data as demo_data_module  # noqa: E402


MAX_STAGED_FILES = 1000
MAX_STAGED_BYTES = 128 * 1024 * 1024
SECRET_INPUT_NAMES = {
    "autonomous_database_admin_password",
    "autonomous_database_wallet_password",
    "autonomous_database_developer_password",
}


def _json_file(path: str, label: str) -> dict[str, object]:
    if not path:
        raise ValueError(f"{label} path is required")
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _required(values: Mapping[str, object], name: str) -> str:
    value = str(values.get(name, "")).strip()
    if not value:
        raise ValueError(f"missing required Deploy Studio input: {name}")
    return value


def _hook_inputs(
    context: Mapping[str, object],
    secrets: Mapping[str, object],
) -> dict[str, object]:
    public_inputs = context.get("inputs", {})
    secret_inputs = secrets.get("inputs", {})
    if not isinstance(public_inputs, dict):
        raise ValueError("Deploy Studio context.inputs must be an object")
    if not isinstance(secret_inputs, dict):
        raise ValueError("Deploy Studio secrets.inputs must be an object")
    inputs = {name: value for name, value in public_inputs.items() if name not in SECRET_INPUT_NAMES}
    inputs.update(secret_inputs)
    if str(inputs.get("autonomous_database_mode", "new")) == "existing":
        inputs["select_ai_grant_schemas"] = _required(inputs, "existing_select_ai_grant_schemas")
    return inputs


def _application(app_id: str) -> dict[str, object]:
    manifest = _json_file(str(ROOT / "apex" / "manifest.json"), "APEX manifest")
    applications = manifest.get("apps", [])
    if not isinstance(applications, list):
        raise ValueError("APEX manifest apps must be a list")
    for application in applications:
        if isinstance(application, dict) and application.get("id") == app_id:
            return application
    raise ValueError(f"unsupported Select AI APEX application: {app_id}")


def _apex_application_url(base_url: str, workspace: str, alias: str) -> str:
    if not base_url.strip():
        return ""
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Terraform returned an invalid APEX URL")
    path = f"/ords/r/{quote(workspace.lower(), safe='')}/{quote(alias.lower(), safe='')}/home"
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


def _demo_folders(raw_schemas: str) -> set[str]:
    manifest = _json_file(str(ROOT / "data" / "manifest.json"), "demo data manifest")
    demos = manifest.get("demos", [])
    if not isinstance(demos, list):
        raise ValueError("demo data manifest demos must be a list")
    folders: dict[str, str] = {}
    for demo in demos:
        if not isinstance(demo, dict):
            continue
        schema = str(demo.get("schema", "")).strip().upper()
        folder = str(demo.get("folder", "")).strip()
        if not schema or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", folder):
            raise ValueError("demo data manifest contains an invalid schema or folder")
        folders[schema] = folder
        aliases = demo.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                normalized = str(alias).strip().upper()
                if normalized:
                    folders[normalized] = folder
    selected = {token for token in re.split(r"[\s,;]+", raw_schemas.upper()) if token}
    return {folders[schema] for schema in selected if schema in folders}


def _safe_archive_parts(name: str) -> tuple[str, ...]:
    if not name or "\\" in name or "\x00" in name:
        raise ValueError("source archive contains an invalid path")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise ValueError("source archive contains an unsafe path")
    return path.parts


def _stage_source_assets(
    archive_path: Path,
    stage_root: Path,
    application: Mapping[str, object],
    raw_schemas: str,
) -> Path:
    export_path = PurePosixPath(_required(application, "export_path"))
    if export_path.is_absolute() or export_path.suffix.lower() not in (".sql", ".zip"):
        raise ValueError("APEX export path must be a relative SQL or ZIP file")
    if not export_path.parts or export_path.parts[0] != "apex" or ".." in export_path.parts:
        raise ValueError("APEX export path must stay under apex/")
    demo_folders = _demo_folders(raw_schemas)
    required_prefixes = {f"data/{folder}/" for folder in demo_folders}
    required_export = export_path.as_posix()
    staged_export = False
    staged_folders: set[str] = set()
    staged_files = 0
    staged_bytes = 0

    try:
        archive = zipfile.ZipFile(archive_path, "r")
    except (FileNotFoundError, zipfile.BadZipFile) as exc:
        raise ValueError("DEPLOY_STUDIO_SOURCE_ARCHIVE must be a valid ZIP archive") from exc

    with archive:
        members: list[tuple[zipfile.ZipInfo, tuple[str, ...]]] = []
        roots: set[str] = set()
        for info in archive.infolist():
            parts = _safe_archive_parts(info.filename)
            roots.add(parts[0])
            if not info.is_dir():
                members.append((info, parts))
        if len(roots) != 1:
            raise ValueError("source archive must contain exactly one GitHub archive root")

        seen_paths: set[str] = set()
        for info, parts in members:
            if len(parts) < 2:
                continue
            relative = PurePosixPath(*parts[1:]).as_posix()
            selected_prefix = next((prefix for prefix in required_prefixes if relative.startswith(prefix)), None)
            if relative != required_export and selected_prefix is None:
                continue
            if relative in seen_paths:
                raise ValueError("source archive contains a duplicate selected path")
            seen_paths.add(relative)
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                raise ValueError("source archive selected assets cannot be symbolic links")
            staged_files += 1
            if staged_files > MAX_STAGED_FILES or staged_bytes + info.file_size > MAX_STAGED_BYTES:
                raise ValueError("selected source assets exceed the staging limit")
            destination = stage_root.joinpath(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, destination.open("wb") as target:
                while chunk := source.read(1024 * 1024):
                    staged_bytes += len(chunk)
                    if staged_bytes > MAX_STAGED_BYTES:
                        raise ValueError("selected source assets exceed the staging limit")
                    target.write(chunk)
            if relative == required_export:
                staged_export = True
            if selected_prefix is not None:
                staged_folders.add(selected_prefix)

    if not staged_export:
        raise ValueError(f"source archive is missing selected APEX export: {required_export}")
    missing_folders = required_prefixes - staged_folders
    if missing_folders:
        raise ValueError("source archive is missing selected demo data")
    manifest_target = stage_root / "data" / "manifest.json"
    manifest_target.parent.mkdir(parents=True, exist_ok=True)
    manifest_target.write_bytes((ROOT / "data" / "manifest.json").read_bytes())
    return stage_root.joinpath(*export_path.parts)


def _installer_arguments(
    context: Mapping[str, object],
    inputs: Mapping[str, object],
    environment: Mapping[str, str],
    output_dir: Path,
    application: Mapping[str, object],
    apex_archive: Path,
) -> list[str]:
    compartment = context.get("compartment", {})
    compartment_id = str(compartment.get("id", "")) if isinstance(compartment, dict) else ""
    mode = str(inputs.get("autonomous_database_mode", "new"))
    wallet_path = _required(environment, "DEPLOY_STUDIO_ADB_WALLET")
    arguments = [
        "install",
        "--mode",
        mode,
        "--oci-config",
        _required(environment, "DEPLOY_STUDIO_OCI_CONFIG"),
        "--oci-key",
        _required(environment, "DEPLOY_STUDIO_OCI_KEY"),
        "--db-version",
        str(inputs.get("autonomous_database_version", "26ai")),
        "--workload",
        str(inputs.get("autonomous_database_workload", "DW")),
        "--model",
        _required(inputs, "select_ai_model"),
        "--schemas",
        _required(inputs, "select_ai_grant_schemas"),
        "--wallet",
        wallet_path,
        "--wallet-password",
        _required(inputs, "autonomous_database_wallet_password"),
        "--admin-password",
        _required(inputs, "autonomous_database_admin_password"),
        "--app-schema-password",
        _required(inputs, "autonomous_database_developer_password"),
        "--apex-password",
        _required(inputs, "autonomous_database_developer_password"),
        "--apex-user",
        str(inputs.get("application_username", "SELECT_AI_ADMIN")),
        "--workspace",
        str(application.get("workspace", "SELECT_AI_APEX")),
        "--apex-alias",
        str(application.get("application_alias", "SELECT_AI_APEX")),
        "--apex-app-name",
        str(application.get("application_name", "Autonomous DB + Select AI")),
        "--apex-archive",
        str(apex_archive),
        "--output-dir",
        str(output_dir),
    ]
    if compartment_id:
        arguments.extend(["--oci-compartment-id", compartment_id])
    if mode == "existing":
        arguments.extend(
            ["--existing-autonomous-database-ocid", _required(inputs, "existing_autonomous_database_ocid")]
        )
    return arguments


def run_hook(
    environment: Mapping[str, str] = os.environ,
    installer: Callable[[Sequence[str]], int] = installer_main,
) -> None:
    context = _json_file(_required(environment, "DEPLOY_STUDIO_CONTEXT"), "Deploy Studio context")
    secrets = _json_file(_required(environment, "DEPLOY_STUDIO_SECRETS"), "Deploy Studio secrets")
    inputs = _hook_inputs(context, secrets)

    with tempfile.TemporaryDirectory(prefix="select-ai-apex-hook-") as temporary:
        stage_root = Path(temporary) / "source"
        output_dir = Path(temporary) / "installer-output"
        application = _application(str(inputs.get("select_ai_apex_app_id", "chatdb-es-2024")))
        apex_archive = _stage_source_assets(
            Path(_required(environment, "DEPLOY_STUDIO_SOURCE_ARCHIVE")),
            stage_root,
            application,
            _required(inputs, "select_ai_grant_schemas"),
        )
        arguments = _installer_arguments(
            context,
            inputs,
            environment,
            output_dir,
            application,
            apex_archive,
        )
        captured = io.StringIO()
        previous_demo_root = demo_data_module.DEMO_ROOT
        demo_data_module.DEMO_ROOT = stage_root / "data"
        try:
            with redirect_stdout(captured), redirect_stderr(captured):
                exit_code = installer(arguments)
        finally:
            demo_data_module.DEMO_ROOT = previous_demo_root
        if exit_code:
            raise RuntimeError("Select AI APEX installer failed")

        terraform_outputs = context.get("terraform_outputs", {})
        safe_outputs = terraform_outputs if isinstance(terraform_outputs, dict) else {}
        application_url = _apex_application_url(
            str(safe_outputs.get("application_url", "")),
            str(application.get("workspace", "SELECT_AI_APEX")),
            str(application.get("application_alias", "SELECT_AI_APEX")),
        )
        report_path = output_dir / "deployment-report.md"
        if application_url:
            report_path.write_text(
                report_path.read_text(encoding="utf-8")
                + f"\n## Application Access\n- URL: `{application_url}`\n",
                encoding="utf-8",
            )
        report = report_path.read_bytes()
        result = {
            "events": [{"level": "success", "message": "Select AI APEX installation completed."}],
            "artifacts": [
                {
                    "name": "deployment-report.md",
                    "content_type": "text/markdown; charset=utf-8",
                    "content_b64": base64.b64encode(report).decode("ascii"),
                }
            ],
            "outputs": {
                **({"application_url": application_url} if application_url else {}),
                **{
                    name: safe_outputs[name]
                    for name in ("adb_db_name", "autonomous_database_id")
                    if name in safe_outputs
                },
            },
        }
        output_path = Path(_required(environment, "DEPLOY_STUDIO_OUTPUT"))
        output_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    run_hook()
