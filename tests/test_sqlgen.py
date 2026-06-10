from dataclasses import replace
from pathlib import Path
import unittest

from select_ai_apex.models import DeploymentOptions
from select_ai_apex.db import split_sql_script
from select_ai_apex.oci_config import OciConfig
from select_ai_apex.sqlgen import object_list_json, render_plan
from select_ai_apex.validators import DbObject


def options() -> DeploymentOptions:
    return DeploymentOptions(
        mode="existing",
        oci_config=OciConfig(
            tenancy="ocid1.tenancy.oc1..aaaa",
            user="ocid1.user.oc1..bbbb",
            fingerprint="aa:bb",
            region="us-chicago-1",
        ),
        oci_private_key="-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
        schemas=["HR"],
        tables=[DbObject("SH", "CUSTOMERS")],
        app_schema_password="SchemaPass123",
        apex_password="ApexPass123",
        wallet=Path("wallet.zip"),
        wallet_password="WalletPass123",
        dsn="selectai_low",
    )


def new_sample_options() -> DeploymentOptions:
    return DeploymentOptions(
        mode="new",
        oci_config=OciConfig(
            tenancy="ocid1.tenancy.oc1..aaaa",
            user="ocid1.user.oc1..bbbb",
            fingerprint="aa:bb",
            region="us-chicago-1",
        ),
        oci_private_key="-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----",
        schemas=["SH"],
        tables=[],
        app_schema_password="SchemaPass123",
        apex_password="ApexPass123",
        wallet=Path("wallet.zip"),
        wallet_password="WalletPass123",
        dsn="selectai_low",
        db_version="19c",
    )


def new_flexcube_options() -> DeploymentOptions:
    return replace(new_sample_options(), schemas=["FLEXCUBE_DEMO"])


class SqlGenerationTests(unittest.TestCase):
    def test_render_plan_uses_grants_not_select_any_table(self) -> None:
        rendered = render_plan(options())

        self.assertNotIn("GRANT SELECT ANY TABLE", rendered.admin_sql)
        self.assertIn('GRANT SELECT ON "SH"."CUSTOMERS" TO SELECT_AI_APP;', rendered.admin_sql)
        self.assertIn("DBMS_CLOUD_AI.CREATE_PROFILE", rendered.app_sql)
        self.assertIn("xai.grok-4-fast-reasoning", rendered.app_sql)
        self.assertIn("APEX_APPLICATION_INSTALL.SET_AUTO_INSTALL_SUP_OBJ(TRUE)", rendered.apex_prelude_sql)
        self.assertIn("CLOUD_AI_PROFILE", rendered.apex_post_sql)

    def test_object_list_prefers_schema_scope_for_future_grants(self) -> None:
        self.assertIn('"owner": "HR"', object_list_json(options()))
        self.assertNotIn('"CUSTOMERS"', object_list_json(options()))

    def test_new_sample_schema_uses_bundled_demo_schema_scope(self) -> None:
        rendered = render_plan(new_sample_options())

        self.assertIn('"owner": "SH_DEMO"', object_list_json(new_sample_options()))
        self.assertNotIn('"owner": "SH"', object_list_json(new_sample_options()))
        self.assertIn("data/demo/sh_demo/install.sql", rendered.admin_sql)
        self.assertIn("CREATE USER SH_DEMO", rendered.admin_sql)
        self.assertIn('CREATE TABLE "SH_DEMO"."SALES"', rendered.admin_sql)
        self.assertIn('GRANT SELECT ON "SH_DEMO"."', rendered.admin_sql)
        self.assertIn("PROMPT Loading SH_DEMO.SALES from SALES.csv", rendered.admin_sql)
        self.assertIn("Bundled Demo Schemas", rendered.report_markdown)

    def test_new_flexcube_schema_uses_manifest_demo_installer(self) -> None:
        rendered = render_plan(new_flexcube_options())

        self.assertIn('"owner": "FLEXCUBE_DEMO"', object_list_json(new_flexcube_options()))
        self.assertIn("data/demo/flexcube_demo/install.sql", rendered.admin_sql)
        self.assertIn("CREATE USER FLEXCUBE_DEMO", rendered.admin_sql)
        self.assertIn("CREATE TABLE \"FLEXCUBE_DEMO\"", rendered.admin_sql)
        self.assertIn("FLEX_STTM_CUSTOMER", rendered.admin_sql)

    def test_report_documents_outputs_and_profile(self) -> None:
        rendered = render_plan(options())

        self.assertIn("Select AI APEX Deployment Report", rendered.report_markdown)
        self.assertIn("`GROK_REASONING`", rendered.report_markdown)
        self.assertIn("secrets.json", rendered.report_markdown)

    def test_split_sql_ignores_export_header_comments_before_plsql(self) -> None:
        statements = split_sql_script(
            """
            -- Oracle APEX export file
            -- Header comments should not change PL/SQL block detection.
            begin
              dbms_output.put_line('ready');
            end;
            /
            """
        )

        self.assertEqual(len(statements), 1)
        self.assertTrue(statements[0].startswith("begin"))
        self.assertIn("dbms_output.put_line", statements[0])
