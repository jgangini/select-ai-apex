import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployStudioContractTests(unittest.TestCase):
    def test_contract_points_to_existing_terraform_and_hook(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], 2)
        self.assertEqual(contract["execution_source"], "oci_resource_manager")
        self.assertEqual(contract["project_id"], "select-ai-apex")
        self.assertTrue((ROOT / contract["terraform"]["path"]).is_dir())
        self.assertTrue((ROOT / contract["post_apply"]["entrypoint"]).is_file())
        self.assertEqual(contract["artifacts"], ["deployment-report.md", "adb_wallet.zip"])
        self.assertEqual(
            contract["post_apply"]["include_paths"],
            ["installer", "apex/manifest.json", "data/manifest.json"],
        )
        self.assertEqual(
            contract["post_apply"]["secret_inputs"],
            [
                "autonomous_database_admin_password",
                "autonomous_database_wallet_password",
                "autonomous_database_developer_password",
            ],
        )
        self.assertTrue(all((ROOT / path).exists() for path in contract["post_apply"]["include_paths"]))

    def test_contract_uses_the_shared_genai_and_database_profile_standard(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))
        capabilities = contract["capabilities"]
        fields = contract["form"]["fields"]
        names = [field["name"] for field in fields]

        self.assertEqual(capabilities["region_selection"], "subscribed_compatible")
        self.assertEqual(capabilities["regional_requirements"], ["genai_chat"])
        self.assertEqual(capabilities["existing_database_wallet"], "required")
        self.assertEqual(capabilities["default_compartment_name"], "select-ai-apex")
        self.assertLess(names.index("autonomous_database_mode"), names.index("existing_autonomous_database_ocid"))
        self.assertLess(names.index("existing_autonomous_database_ocid"), names.index("autonomous_database_version"))
        profile = next(field for field in fields if field["name"] == "autonomous_database_version")
        database_ocid = next(field for field in fields if field["name"] == "existing_autonomous_database_ocid")
        workspace_username = next(field for field in fields if field["name"] == "application_username")
        workspace_password = next(field for field in fields if field["name"] == "autonomous_database_developer_password")
        model = next(field for field in fields if field["name"] == "select_ai_model")
        new_database_schemas = next(field for field in fields if field["name"] == "select_ai_grant_schemas")
        existing_database_schemas = next(field for field in fields if field["name"] == "existing_select_ai_grant_schemas")
        self.assertEqual(profile["transform"], "database_profile")
        self.assertEqual(profile["visible_when"], {"field": "autonomous_database_mode", "equals": "new"})
        self.assertEqual(database_ocid["label"], "Database OCID")
        self.assertTrue(database_ocid["required"])
        self.assertEqual(database_ocid["type"], "text")
        self.assertEqual(database_ocid["visible_when"], {"field": "autonomous_database_mode", "equals": "existing"})
        self.assertEqual(workspace_username["label"], "APEX workspace username")
        self.assertEqual(workspace_password["label"], "APEX workspace password")
        self.assertEqual(model["group"], "enterprise_ai")
        self.assertEqual(model["options_source"], "oci_genai_chat_models")
        self.assertEqual(new_database_schemas["default"], "SH_DEMO,FLEXCUBE_DEMO")
        self.assertTrue(new_database_schemas["multiple"])
        self.assertEqual(new_database_schemas["visible_when"], {"field": "autonomous_database_mode", "equals": "new"})
        self.assertTrue(existing_database_schemas["multiple"])
        self.assertEqual(existing_database_schemas["options_source"], "oci_autonomous_database_schemas")
        self.assertEqual(existing_database_schemas["visible_when"], {"field": "autonomous_database_mode", "equals": "existing"})

    def test_declarative_layout_and_email_keep_shared_controls_and_access_without_oci_keys(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))
        form = contract["form"]
        groups = form["groups"]
        self.assertEqual([group["id"] for group in groups], [
            "credentials", "services", "database", "enterprise_ai", "apex_application",
        ])
        self.assertEqual([item["name"] for item in groups[0]["items"]], ["oci_config", "oci_key"])
        self.assertIn("database_wallet", [item["name"] for item in groups[2]["items"]])
        self.assertCountEqual(
            [item["name"] for group in groups for item in group["items"] if item["kind"] == "field"],
            [field["name"] for field in form["fields"]],
        )
        self.assertEqual(form["email_access_fields"], [
            "application_username", "autonomous_database_developer_password",
        ])
        database, apex = contract["email"]["services"]
        self.assertEqual(database["title"], "Autonomous Database")
        self.assertEqual(apex["title"], "Oracle APEX")
        self.assertTrue(any(field.get("link") and field.get("output") == "application_url" for field in apex["fields"]))
        self.assertCountEqual(contract["email"]["attachments"], [
            "adb_wallet.zip", "deployment-report.md", "deployment.log", "resource-manager-terraform-source.zip",
        ])
        self.assertFalse(contract["terraform"]["package_oci_credentials"])

    def test_declared_outputs_are_not_secrets(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))
        forbidden = ("password", "private_key", "wallet_base64", "secret")

        self.assertFalse(any(token in name.lower() for name in contract["outputs"] for token in forbidden))

    def test_chat_db_and_ask_oracle_v5002_are_distinct_choices(self) -> None:
        manifest = json.loads((ROOT / "apex" / "manifest.json").read_text(encoding="utf-8"))
        chat_db, ask_oracle = manifest["apps"]
        self.assertEqual((chat_db["id"], chat_db["label"]), ("chatdb-es-2024", "Chat DB"))
        self.assertEqual((ask_oracle["id"], ask_oracle["label"]), ("ask-oracle-chatbot-2026-11-18", "Ask Oracle 5.0.0.2"))
        self.assertEqual(manifest["default_app"], ask_oracle["id"])
        self.assertNotEqual(chat_db["workspace"], ask_oracle["workspace"])
        self.assertNotEqual(chat_db["parsing_schema"], ask_oracle["parsing_schema"])
        self.assertEqual(ask_oracle["application_version"], "5.0.0.2")
        export = ROOT / ask_oracle["export_path"]

        self.assertEqual(set((ROOT / "apex").glob("*.sql")), {export, ROOT / chat_db["export_path"]})
        self.assertEqual(export.stat().st_size, ask_oracle["source"]["size_bytes"])
        self.assertEqual(hashlib.sha256(export.read_bytes()).hexdigest(), ask_oracle["source"]["sha256"])
        for application in manifest["apps"]:
            with (ROOT / application["export_path"]).open(encoding="utf-8") as sql:
                self.assertIn(f"p_release=>'{application['minimum_apex_version']}'", sql.read(4096))
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))
        field, = [field for field in contract["form"]["fields"] if field["name"] == "select_ai_apex_app_id"]
        self.assertEqual(field["label"], "APEX application")
        self.assertEqual(field["default"], ask_oracle["id"])
        self.assertEqual(field["options"], [
            {"value": application["id"], "label": application["label"]} for application in manifest["apps"]
        ])


if __name__ == "__main__":
    unittest.main()
