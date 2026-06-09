from __future__ import annotations

import json

from .models import DeploymentOptions, RenderedPlan
from .validators import csv_quote, q_quote, sql_identifier, sql_string


def object_list_json(options: DeploymentOptions) -> str:
    entries: list[dict[str, str]] = []
    if options.schemas:
        entries.extend({"owner": owner} for owner in options.schemas)
    elif options.tables:
        entries.extend({"owner": obj.owner, "name": obj.name} for obj in options.tables)
    return json.dumps(entries, indent=2)


def render_grants(options: DeploymentOptions) -> str:
    app_schema = sql_identifier(options.app_schema)
    statements: list[str] = []
    if options.schemas:
        owner_list = csv_quote(options.schemas)
        object_types = csv_quote(["TABLE", "VIEW", "MATERIALIZED VIEW"])
        statements.append(
            f"""DECLARE
  l_sql VARCHAR2(32767);
BEGIN
  FOR obj IN (
    SELECT owner, object_name
      FROM all_objects
     WHERE owner IN ({owner_list})
       AND object_type IN ({object_types})
  ) LOOP
    l_sql := 'GRANT SELECT ON "' || obj.owner || '"."' || obj.object_name || '" TO {app_schema}';
    BEGIN
      EXECUTE IMMEDIATE l_sql;
    EXCEPTION
      WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('WARN grant failed: ' || l_sql || ' -> ' || SQLERRM);
    END;
  END LOOP;
END;
/"""
        )
    for obj in options.tables:
        statements.append(f'GRANT SELECT ON "{obj.owner}"."{obj.name}" TO {app_schema};')
    return "\n\n".join(statements)


def render_admin_sql(options: DeploymentOptions) -> str:
    app_schema = sql_identifier(options.app_schema)
    workspace = sql_identifier(options.workspace)
    apex_user = sql_identifier(options.apex_user)
    password = options.app_schema_password
    apex_password = options.apex_password
    network_acl = ""
    if options.network_acl_host:
        network_acl = f"""

BEGIN
  DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(
    host => {sql_string(options.network_acl_host)},
    ace  => xs$ace_type(
      privilege_list => xs$name_list('http'),
      principal_name => {sql_string(app_schema)},
      principal_type => xs_acl.ptype_db));
END;
/"""

    return f"""SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

DECLARE
  l_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO l_count FROM dba_users WHERE username = {sql_string(app_schema)};
  IF l_count = 0 THEN
    EXECUTE IMMEDIATE 'CREATE USER {app_schema} IDENTIFIED BY "{password}" DEFAULT TABLESPACE DATA QUOTA UNLIMITED ON DATA';
  ELSE
    EXECUTE IMMEDIATE 'ALTER USER {app_schema} IDENTIFIED BY "{password}" ACCOUNT UNLOCK';
    EXECUTE IMMEDIATE 'ALTER USER {app_schema} QUOTA UNLIMITED ON DATA';
  END IF;
END;
/

GRANT CREATE SESSION TO {app_schema};
GRANT CREATE TABLE TO {app_schema};
GRANT CREATE VIEW TO {app_schema};
GRANT CREATE PROCEDURE TO {app_schema};
GRANT CREATE TRIGGER TO {app_schema};
GRANT CREATE SEQUENCE TO {app_schema};
GRANT CREATE SYNONYM TO {app_schema};
GRANT DWROLE TO {app_schema};
GRANT EXECUTE ON DBMS_CLOUD TO {app_schema};
GRANT EXECUTE ON DBMS_CLOUD_AI TO {app_schema};

BEGIN
  EXECUTE IMMEDIATE 'GRANT EXECUTE ON DBMS_CLOUD_PIPELINE TO {app_schema}';
EXCEPTION
  WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('WARN optional DBMS_CLOUD_PIPELINE grant skipped: ' || SQLERRM);
END;
/

BEGIN
  EXECUTE IMMEDIATE 'GRANT EXECUTE ON DBMS_VECTOR TO {app_schema}';
EXCEPTION
  WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('WARN optional DBMS_VECTOR grant skipped: ' || SQLERRM);
END;
/
{render_grants(options)}
{network_acl}

DECLARE
  l_workspace_count NUMBER;
BEGIN
  SELECT COUNT(*) INTO l_workspace_count
    FROM apex_workspaces
   WHERE workspace = {sql_string(workspace)};

  IF l_workspace_count = 0 THEN
    APEX_INSTANCE_ADMIN.ADD_WORKSPACE(
      p_workspace          => {sql_string(workspace)},
      p_primary_schema     => {sql_string(app_schema)},
      p_additional_schemas => NULL);
  ELSE
    BEGIN
      APEX_INSTANCE_ADMIN.ADD_SCHEMA(
        p_workspace             => {sql_string(workspace)},
        p_schema                => {sql_string(app_schema)},
        p_grant_apex_privileges => TRUE);
    EXCEPTION
      WHEN OTHERS THEN
        IF SQLCODE NOT IN (-20001, -20987) THEN
          DBMS_OUTPUT.PUT_LINE('WARN schema mapping may already exist: ' || SQLERRM);
        END IF;
    END;
  END IF;
END;
/

DECLARE
  l_user_id NUMBER;
BEGIN
  APEX_UTIL.SET_SECURITY_GROUP_ID(APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => {sql_string(workspace)}));
  l_user_id := APEX_UTIL.GET_USER_ID({sql_string(apex_user)});
  IF l_user_id IS NULL THEN
    APEX_UTIL.CREATE_USER(
      p_user_name                    => {sql_string(apex_user)},
      p_web_password                 => {sql_string(apex_password)},
      p_developer_privs              => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
      p_default_schema               => {sql_string(app_schema)},
      p_allow_access_to_schemas      => {sql_string(app_schema)},
      p_change_password_on_first_use => 'N',
      p_allow_app_building_yn        => 'Y',
      p_allow_sql_workshop_yn        => 'Y');
  ELSE
    APEX_UTIL.EDIT_USER(
      p_user_id                      => l_user_id,
      p_user_name                    => {sql_string(apex_user)},
      p_web_password                 => {sql_string(apex_password)},
      p_new_password                 => {sql_string(apex_password)},
      p_default_schema               => {sql_string(app_schema)},
      p_allow_access_to_schemas      => {sql_string(app_schema)},
      p_developer_roles              => 'ADMIN:CREATE:DATA_LOADER:EDIT:HELP:MONITOR:SQL',
      p_account_locked               => 'N',
      p_change_password_on_first_use => 'N');
  END IF;
END;
/

COMMIT;
"""


def render_app_sql(options: DeploymentOptions) -> str:
    attrs: dict[str, object] = {
        "provider": "oci",
        "credential_name": options.credential_name,
        "object_list": json.loads(object_list_json(options)),
        "model": options.model,
        "comments": True,
        "constraints": True,
        "conversation": True,
        "object_list_mode": "all",
        "region": options.oci_config.region,
    }
    if options.oci_compartment_id:
        attrs["oci_compartment_id"] = options.oci_compartment_id
    attributes = json.dumps(attrs, indent=2)

    return f"""SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

BEGIN
  BEGIN
    DBMS_CLOUD.DROP_CREDENTIAL(credential_name => {sql_string(options.credential_name)});
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE NOT IN (-20000, -27476) THEN
        DBMS_OUTPUT.PUT_LINE('WARN credential drop skipped: ' || SQLERRM);
      END IF;
  END;

  DBMS_CLOUD.CREATE_CREDENTIAL(
    credential_name => {sql_string(options.credential_name)},
    user_ocid       => {sql_string(options.oci_config.user)},
    tenancy_ocid    => {sql_string(options.oci_config.tenancy)},
    private_key     => {q_quote(options.oci_private_key)},
    fingerprint     => {sql_string(options.oci_config.fingerprint)});
END;
/

BEGIN
  DBMS_CLOUD_AI.DROP_PROFILE(profile_name => {sql_string(options.profile_name)}, force => TRUE);
EXCEPTION
  WHEN OTHERS THEN
    DBMS_OUTPUT.PUT_LINE('WARN profile drop skipped: ' || SQLERRM);
END;
/

BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => {sql_string(options.profile_name)},
    attributes   => {q_quote(attributes)});
  DBMS_CLOUD_AI.SET_PROFILE(profile_name => {sql_string(options.profile_name)});
END;
/

COMMIT;
"""


def render_apex_prelude_sql(options: DeploymentOptions) -> str:
    application_id_sql = (
        f"  APEX_APPLICATION_INSTALL.SET_APPLICATION_ID({options.apex_application_id});"
        if options.apex_application_id
        else "  APEX_APPLICATION_INSTALL.GENERATE_APPLICATION_ID;"
    )
    return f"""SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

BEGIN
  APEX_APPLICATION_INSTALL.CLEAR_ALL;
  APEX_APPLICATION_INSTALL.SET_WORKSPACE({sql_string(options.workspace)});
{application_id_sql}
  APEX_APPLICATION_INSTALL.GENERATE_OFFSET;
  APEX_APPLICATION_INSTALL.SET_SCHEMA({sql_string(options.app_schema)});
  APEX_APPLICATION_INSTALL.SET_APPLICATION_ALIAS({sql_string(options.apex_alias)});
  APEX_APPLICATION_INSTALL.SET_APPLICATION_NAME({sql_string(options.apex_app_name)});
  APEX_APPLICATION_INSTALL.SET_AUTO_INSTALL_SUP_OBJ(TRUE);
END;
/
"""


def render_apex_post_sql(options: DeploymentOptions) -> str:
    return f"""SET DEFINE OFF
WHENEVER SQLERROR EXIT SQL.SQLCODE ROLLBACK

BEGIN
  APEX_UTIL.SET_SECURITY_GROUP_ID(APEX_UTIL.FIND_SECURITY_GROUP_ID(p_workspace => {sql_string(options.workspace)}));
  APEX_UTIL.SET_PREFERENCE(
    p_preference => 'CLOUD_AI_PROFILE',
    p_value      => LOWER({sql_string(options.profile_name)}),
    p_user       => {sql_string(options.apex_user)});
END;
/

COMMIT;
"""


def render_plan(options: DeploymentOptions) -> RenderedPlan:
    admin_sql = render_admin_sql(options)
    app_sql = render_app_sql(options)
    apex_prelude_sql = render_apex_prelude_sql(options)
    apex_post_sql = render_apex_post_sql(options)
    executed_steps = "\n\n".join(
        [
            "-- 01_admin_bootstrap.sql",
            admin_sql,
            "-- 02_select_ai_profile.sql",
            app_sql,
            "-- 03_apex_import_prelude.sql",
            apex_prelude_sql,
            f"-- APEX export imported from {options.apex_archive.as_posix()}",
            "-- 04_apex_post_install.sql",
            apex_post_sql,
        ]
    )
    report = render_report(options)
    secrets = json.dumps(
        {
            "app_schema": options.app_schema,
            "app_schema_password": options.app_schema_password,
            "apex_user": options.apex_user,
            "apex_password": options.apex_password,
            "wallet_password": options.wallet_password,
        },
        indent=2,
    )
    return RenderedPlan(
        admin_sql=admin_sql,
        app_sql=app_sql,
        apex_prelude_sql=apex_prelude_sql,
        apex_post_sql=apex_post_sql,
        executed_steps_sql=executed_steps,
        report_markdown=report,
        secrets_json=secrets,
    )


def render_report(options: DeploymentOptions) -> str:
    object_scope = object_list_json(options)
    dsn = options.dsn or "(selected at runtime)"
    app_id = str(options.apex_application_id) if options.apex_application_id else "generated by APEX"
    return f"""# Select AI APEX Deployment Report

## Requested Deployment
- Mode: `{options.mode}`
- Database version: `{options.db_version}`
- Workload: `{options.workload}`
- Workspace: `{options.workspace}`
- Parsing schema: `{options.app_schema}`
- APEX application alias: `{options.apex_alias}`
- APEX application ID: `{app_id}`
- APEX user: `{options.apex_user}`
- Wallet DSN: `{dsn}`

## Select AI Profile
- Profile: `{options.profile_name}`
- Credential: `{options.credential_name}`
- Provider: `oci`
- Model: `{options.model}`
- Region: `{options.oci_config.region}`

## Data Scope
```json
{object_scope}
```

## Executed Steps
1. Create or reuse the parsing/profile schema and grant required database privileges.
2. Grant `SELECT` on the requested schemas/tables to the parsing schema.
3. Create or reuse the APEX workspace and workspace administrator.
4. Create the OCI API-key credential through `DBMS_CLOUD.CREATE_CREDENTIAL`.
5. Recreate the Select AI profile through `DBMS_CLOUD_AI.CREATE_PROFILE`.
6. Import the APEX export with supporting objects enabled.
7. Set the APEX `CLOUD_AI_PROFILE` preference for the generated workspace user.

## Notes
- Secrets are written only to `outputs/secrets.json`, which is ignored by git.
- The generated SQL avoids `SELECT ANY TABLE`; data access is controlled by object grants.
- For OCI Generative AI, Oracle documentation says network ACL is not required. A network ACL block is rendered only when `--network-acl-host` is provided.
"""
