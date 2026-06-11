from __future__ import annotations

from dataclasses import dataclass
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
from .oci_config import OciConfig
from .validators import DbObject


@dataclass(frozen=True)
class DeploymentOptions:
    mode: str
    oci_config: OciConfig
    oci_private_key: str
    schemas: list[str]
    tables: list[DbObject]
    output_dir: Path = DEFAULT_OUTPUT_DIR
    workspace: str = DEFAULT_WORKSPACE
    app_schema: str = DEFAULT_APP_SCHEMA
    app_schema_password: str = ""
    profile_name: str = DEFAULT_PROFILE_NAME
    credential_name: str = DEFAULT_CREDENTIAL_NAME
    model: str = DEFAULT_MODEL
    apex_alias: str = DEFAULT_APEX_ALIAS
    apex_app_name: str = DEFAULT_APEX_APP_NAME
    apex_user: str = DEFAULT_APEX_USER
    apex_password: str = ""
    apex_archive: Path = DEFAULT_APEX_ARCHIVE
    apex_application_id: int | None = None
    oci_compartment_id: str | None = None
    network_acl_host: str | None = None
    wallet: Path | None = None
    wallet_password: str = ""
    dsn: str = ""
    admin_user: str = "ADMIN"
    admin_password: str = ""
    db_version: str = "26ai"
    workload: str = "OLTP"
    existing_autonomous_database_ocid: str | None = None


@dataclass(frozen=True)
class RenderedPlan:
    admin_sql: str
    app_sql: str
    apex_prelude_sql: str
    apex_post_sql: str
    executed_steps_sql: str
    report_markdown: str
    secrets_json: str
