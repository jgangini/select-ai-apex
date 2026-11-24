from dataclasses import replace
from pathlib import Path
import unittest

from installer.models import DeploymentOptions
from installer.db import split_sql_script
from installer.oci_config import OciConfig
from installer.sqlgen import object_list_json, render_plan, render_report
from installer.validators import DbObject


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
        self.assertIn('GRANT SELECT ON "SH"."CUSTOMERS" TO SELECT_AI_APP_5002;', rendered.admin_sql)
        self.assertIn("GRANT EXECUTE ON DBMS_CLOUD_AI_AGENT TO SELECT_AI_APP_5002;", rendered.admin_sql)
        self.assertIn("DBMS_CLOUD_AI.CREATE_PROFILE", rendered.app_sql)
        self.assertIn("xai.grok-4-fast-reasoning", rendered.app_sql)
        self.assertIn("APEX_APPLICATION_INSTALL.SET_AUTO_INSTALL_SUP_OBJ(TRUE)", rendered.apex_prelude_sql)
        self.assertIn("CLOUD_AI_PROFILE", rendered.apex_post_sql)
        self.assertIn("ALTER PROCEDURE PROCESS_PROMPT_REQUEST COMPILE", rendered.apex_post_sql)
        self.assertIn("Ask Oracle PROCESS_PROMPT_REQUEST did not compile", rendered.apex_post_sql)

    def test_ask_oracle_profiles_have_room_for_larger_nl2sql_responses(self) -> None:
        ask_oracle = render_plan(replace(options(), model="ocid1.generativeaimodel.oc1.us-chicago-1.example"))
        self.assertIn('"max_tokens": 8192', ask_oracle.app_sql)
        self.assertIn("SYS.ODCIVARCHAR2LIST", ask_oracle.app_sql)
        self.assertIn("only the tables in the supplied profile metadata", ask_oracle.app_sql)
        chat_db = render_plan(replace(options(), apex_alias="SELECT_AI_APEX"))
        self.assertNotIn('"max_tokens"', chat_db.app_sql)

    def test_ask_oracle_initializes_nl2sql_without_overwriting_a_user_selection(self) -> None:
        rendered = render_plan(replace(options(), apex_user="APEX_TEST", profile_name="CUSTOM_PROFILE"))
        for preference, value in (("CONVERSATION_STYLE", "CHAT_WITH_DB"), ("CLOUD_AI_PROFILE1", "CUSTOM_PROFILE")):
            with self.subTest(preference=preference):
                self.assertIn(
                    f"IF APEX_UTIL.GET_PREFERENCE(p_preference => '{preference}', p_user => 'APEX_TEST') IS NULL THEN\n"
                    f"    APEX_UTIL.SET_PREFERENCE(p_preference => '{preference}', p_value => '{value}', p_user => 'APEX_TEST');",
                    rendered.apex_post_sql,
                )
        chat_db = render_plan(replace(options(), apex_alias="SELECT_AI_APEX"))
        self.assertNotIn("CONVERSATION_STYLE", chat_db.apex_post_sql)
        self.assertNotIn("CLOUD_AI_PROFILE1", chat_db.apex_post_sql)
        self.assertIn("'CLOUD_AI_PROFILE'", chat_db.apex_post_sql)

    def test_ask_oracle_initializes_the_catalog_map_only_when_absent(self) -> None:
        ask_oracle = render_plan(options()).apex_post_sql
        self.assertIn(
            "FROM USER_TABLES WHERE TABLE_NAME = 'ASK_ORACLE_DATA_CATALOG_MAP';\n"
            "  IF l_exists = 0 THEN\n"
            "    EXECUTE IMMEDIATE q'[\n"
            "      CREATE TABLE ASK_ORACLE_DATA_CATALOG_MAP (",
            ask_oracle,
        )
        self.assertIn("view_name     VARCHAR2(128) NOT NULL", ask_oracle)
        chat_db = render_plan(replace(options(), apex_alias="SELECT_AI_APEX")).apex_post_sql
        self.assertNotIn("ASK_ORACLE_DATA_CATALOG_MAP", chat_db)

    def test_object_list_prefers_schema_scope_for_future_grants(self) -> None:
        self.assertIn('"owner": "HR"', object_list_json(options()))
        self.assertNotIn('"CUSTOMERS"', object_list_json(options()))

    def test_new_sample_schema_uses_bundled_demo_schema_scope(self) -> None:
        rendered = render_plan(new_sample_options())

        self.assertIn('"owner": "SH_DEMO"', object_list_json(new_sample_options()))
        self.assertNotIn('"owner": "SH"', object_list_json(new_sample_options()))
        self.assertIn("data/sh_demo/manifest.json", rendered.admin_sql)
        self.assertIn("CREATE USER SH_DEMO", rendered.admin_sql)
        self.assertIn('CREATE TABLE "SH_DEMO"."SALES"', rendered.admin_sql)
        self.assertIn('GRANT SELECT ON "SH_DEMO"."', rendered.admin_sql)
        self.assertIn("CSV rows are loaded by the Select AI Apex loader", rendered.admin_sql)
        self.assertIn("Bundled Demo Schemas", rendered.report_markdown)

    def test_new_flexcube_schema_uses_manifest_demo_installer(self) -> None:
        rendered = render_plan(new_flexcube_options())

        self.assertIn('"owner": "FLEXCUBE_DEMO"', object_list_json(new_flexcube_options()))
        self.assertIn("data/flexcube_demo/manifest.json", rendered.admin_sql)
        self.assertIn("CREATE USER FLEXCUBE_DEMO", rendered.admin_sql)
        self.assertIn("CREATE TABLE \"FLEXCUBE_DEMO\"", rendered.admin_sql)
        self.assertIn("FLEX_STTM_CUSTOMER", rendered.admin_sql)

    def test_report_documents_outputs_and_profile(self) -> None:
        rendered = render_plan(options())

        self.assertIn("Select AI APEX Deployment Report", rendered.report_markdown)
        self.assertIn("`SELECT_AI_CHAT`", rendered.report_markdown)
        self.assertIn("legacy profile cleanup", rendered.app_sql)
        self.assertIn("secrets.json", rendered.report_markdown)
        self.assertIn("APEX application ID: `100`", render_report(options(), installed_application_id=100))

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
