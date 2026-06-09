from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path

from .constants import (
    DEFAULT_APEX_ALIAS,
    DEFAULT_APEX_APP_NAME,
    DEFAULT_APEX_ARCHIVE,
    DEFAULT_APEX_USER,
    DEFAULT_APP_SCHEMA,
    DEFAULT_CREDENTIAL_NAME,
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PROFILE_NAME,
    DEFAULT_WORKSPACE,
)
from .db import connect_with_wallet, execute_sql_text
from .models import DeploymentOptions
from .oci_config import read_oci_config
from .report import write_rendered_plan
from .secrets import generate_oracle_password
from .sqlgen import render_plan
from .terraform_vars import write_terraform_tfvars
from .validators import ValidationError, normalize_csv_identifiers, normalize_db_objects, validate_ocid
from .wallet import extract_wallet, list_wallet_dsn_aliases


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="select-ai-apex", description="Deploy Select AI + APEX on Autonomous Database.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "install"):
        sub = subparsers.add_parser(name, help=f"{name} deployment assets")
        add_common_arguments(sub)
    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--mode", choices=["new", "existing"], required=True)
    parser.add_argument("--oci-config", type=Path, required=True)
    parser.add_argument("--oci-profile", default="DEFAULT")
    parser.add_argument("--oci-key", type=Path, required=True)
    parser.add_argument("--oci-compartment-id")
    parser.add_argument("--existing-autonomous-database-ocid")
    parser.add_argument("--db-version", choices=["19c", "26ai"], default="26ai")
    parser.add_argument("--workload", choices=["OLTP", "DW"], default="OLTP")
    parser.add_argument("--schemas", default="")
    parser.add_argument("--tables", default="")
    parser.add_argument("--wallet", type=Path)
    parser.add_argument("--wallet-password", default="")
    parser.add_argument("--dsn", default="")
    parser.add_argument("--admin-user", default="ADMIN")
    parser.add_argument("--admin-password", default="")
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    parser.add_argument("--app-schema", default=DEFAULT_APP_SCHEMA)
    parser.add_argument("--app-schema-password", default="")
    parser.add_argument("--profile-name", default=DEFAULT_PROFILE_NAME)
    parser.add_argument("--credential-name", default=DEFAULT_CREDENTIAL_NAME)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--apex-alias", default=DEFAULT_APEX_ALIAS)
    parser.add_argument("--apex-app-name", default=DEFAULT_APEX_APP_NAME)
    parser.add_argument("--apex-user", default=DEFAULT_APEX_USER)
    parser.add_argument("--apex-password", default="")
    parser.add_argument("--apex-archive", type=Path, default=DEFAULT_APEX_ARCHIVE)
    parser.add_argument("--apex-application-id", type=int)
    parser.add_argument("--network-acl-host")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)


def options_from_args(args: argparse.Namespace) -> DeploymentOptions:
    oci_config = read_oci_config(args.oci_config, profile=args.oci_profile)
    oci_private_key = args.oci_key.read_text(encoding="utf-8")
    schemas = normalize_csv_identifiers(args.schemas, "schema")
    tables = normalize_db_objects(args.tables)
    if not schemas and not tables:
        raise ValidationError("provide at least one schema with --schemas or one table with --tables")
    app_schema_password = args.app_schema_password or generate_oracle_password()
    apex_password = args.apex_password or generate_oracle_password()
    compartment_id = validate_ocid(args.oci_compartment_id, "oci_compartment_id")
    existing_adb_ocid = validate_ocid(args.existing_autonomous_database_ocid, "existing_autonomous_database_ocid")

    wallet = args.wallet
    dsn = args.dsn
    if wallet and not dsn:
        aliases = list_wallet_dsn_aliases(wallet)
        dsn = aliases[0] if aliases else ""
    return DeploymentOptions(
        mode=args.mode,
        oci_config=oci_config,
        oci_private_key=oci_private_key,
        schemas=schemas,
        tables=tables,
        output_dir=args.output_dir,
        workspace=args.workspace,
        app_schema=args.app_schema,
        app_schema_password=app_schema_password,
        profile_name=args.profile_name,
        credential_name=args.credential_name,
        model=args.model,
        apex_alias=args.apex_alias,
        apex_app_name=args.apex_app_name,
        apex_user=args.apex_user,
        apex_password=apex_password,
        apex_archive=args.apex_archive,
        apex_application_id=args.apex_application_id,
        oci_compartment_id=compartment_id,
        network_acl_host=args.network_acl_host,
        wallet=wallet,
        wallet_password=args.wallet_password,
        dsn=dsn,
        admin_user=args.admin_user,
        admin_password=args.admin_password,
        db_version=args.db_version,
        workload=args.workload,
        existing_autonomous_database_ocid=existing_adb_ocid,
    )


def find_apex_export(apex_archive: Path, target_dir: Path) -> Path:
    if apex_archive.suffix.lower() == ".sql":
        return apex_archive
    if apex_archive.suffix.lower() != ".zip":
        raise ValidationError("APEX artifact must be a .sql export or .zip containing one .sql export")
    with zipfile.ZipFile(apex_archive, "r") as archive:
        sql_files = [name for name in archive.namelist() if name.lower().endswith(".sql")]
        if len(sql_files) != 1:
            raise ValidationError("APEX zip must contain exactly one .sql export")
        target_dir.mkdir(parents=True, exist_ok=True)
        archive.extract(sql_files[0], target_dir)
        return target_dir / sql_files[0]


def run_plan(args: argparse.Namespace) -> int:
    options = options_from_args(args)
    rendered = render_plan(options)
    write_rendered_plan(rendered, options.output_dir)
    write_terraform_tfvars(options, args.oci_key, options.output_dir)
    print(f"Wrote deployment plan to {options.output_dir}")
    return 0


def run_install(args: argparse.Namespace) -> int:
    options = options_from_args(args)
    missing = []
    if not options.wallet:
        missing.append("--wallet")
    if not options.wallet_password:
        missing.append("--wallet-password")
    if not options.admin_password:
        missing.append("--admin-password")
    if not options.dsn:
        missing.append("--dsn or a wallet with tnsnames.ora")
    if missing:
        raise ValidationError("install requires " + ", ".join(missing))

    rendered = render_plan(options)
    write_rendered_plan(rendered, options.output_dir)
    write_terraform_tfvars(options, args.oci_key, options.output_dir)

    with tempfile.TemporaryDirectory(prefix="select-ai-apex-") as tmp:
        tmp_path = Path(tmp)
        wallet_dir = extract_wallet(options.wallet, tmp_path / "wallet")  # type: ignore[arg-type]
        apex_export = find_apex_export(options.apex_archive, tmp_path / "apex")

        admin_connection = connect_with_wallet(
            user=options.admin_user,
            password=options.admin_password,
            dsn=options.dsn,
            wallet_dir=wallet_dir,
            wallet_password=options.wallet_password,
        )
        try:
            execute_sql_text(admin_connection, rendered.admin_sql)
        finally:
            admin_connection.close()

        app_connection = connect_with_wallet(
            user=options.app_schema,
            password=options.app_schema_password,
            dsn=options.dsn,
            wallet_dir=wallet_dir,
            wallet_password=options.wallet_password,
        )
        try:
            execute_sql_text(app_connection, rendered.app_sql)
            execute_sql_text(app_connection, rendered.apex_prelude_sql)
            execute_sql_text(app_connection, apex_export.read_text(encoding="utf-8", errors="replace"))
            execute_sql_text(app_connection, rendered.apex_post_sql)
        finally:
            app_connection.close()

    print(f"Install completed. Report: {options.output_dir / 'deployment-report.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            return run_plan(args)
        if args.command == "install":
            return run_install(args)
    except ValidationError as exc:
        parser.error(str(exc))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
