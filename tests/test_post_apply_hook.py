import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from deploy.hooks.post_apply import _application, _hook_inputs, _stage_source_assets, run_hook
from installer import demo_data


class PostApplyHookTests(unittest.TestCase):
    def test_source_staging_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_archive = root / "source.zip"
            with zipfile.ZipFile(source_archive, "w") as archive:
                archive.writestr("select-ai-apex-deadbeef/../apex/chatdb-es-2024.sql", "unsafe")

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                _stage_source_assets(
                    source_archive,
                    root / "stage",
                    _application("chatdb-es-2024"),
                    "SH_DEMO",
                )

    def test_hook_stages_only_selected_assets_and_emits_safe_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            context = root / "context.json"
            secrets = root / "secrets.json"
            output = root / "output.json"
            config = root / "config"
            key = root / "key.pem"
            wallet = root / "wallet.zip"
            source_archive = root / "source.zip"
            context.write_text(
                json.dumps(
                    {
                        "compartment": {"id": "ocid1.compartment.oc1..example"},
                        "inputs": {
                            "autonomous_database_mode": "existing",
                            "existing_autonomous_database_ocid": "ocid1.autonomousdatabase.oc1..example",
                            "autonomous_database_version": "26ai",
                            "autonomous_database_workload": "DW",
                            "select_ai_model": "cohere.command-a-03-2025",
                            "select_ai_grant_schemas": "SH",
                            "select_ai_apex_app_id": "chatdb-es-2024",
                            "application_username": "SELECT_AI_ADMIN",
                            "autonomous_database_admin_password": "PublicAdminMustNotWin",
                            "autonomous_database_wallet_password": "PublicWalletMustNotWin",
                            "autonomous_database_developer_password": "PublicDeveloperMustNotWin",
                            "select_ai_schema_passwords": {"SH": "PublicSchemaMustNotWin"},
                        },
                        "terraform_outputs": {
                            "application_url": "https://example.invalid/ords/",
                            "adb_db_name": "SELECTAI",
                            "autonomous_database_id": "ocid1.autonomousdatabase.oc1..example",
                        },
                    }
                ),
                encoding="utf-8",
            )
            secrets.write_text(
                json.dumps(
                    {
                        "inputs": {
                            "autonomous_database_admin_password": "AdminPass123",
                            "autonomous_database_wallet_password": "WalletPass123",
                            "autonomous_database_developer_password": "DeveloperPass123",
                        },
                        "select_ai_schema_passwords": {"SH": "SchemaPass123"},
                    }
                ),
                encoding="utf-8",
            )
            config.write_text("[DEFAULT]\nregion=us-chicago-1\n", encoding="utf-8")
            key.write_text("test-key", encoding="utf-8")
            wallet.write_bytes(b"test-wallet")
            with zipfile.ZipFile(source_archive, "w") as archive:
                archive.writestr("select-ai-apex-deadbeef/apex/chatdb-es-2024.sql", "-- selected export")
                archive.writestr("select-ai-apex-deadbeef/apex/ADB-AskOracle-Chatbot-2026-03-04.sql", "-- other export")
                archive.writestr("select-ai-apex-deadbeef/data/sh_demo/data/example.json", "{}")
                archive.writestr("select-ai-apex-deadbeef/data/flexcube_demo/data/example.json", "{}")
                archive.writestr("select-ai-apex-deadbeef/README.md", "not staged")
            environment = {
                "DEPLOY_STUDIO_CONTEXT": str(context),
                "DEPLOY_STUDIO_SECRETS": str(secrets),
                "DEPLOY_STUDIO_OUTPUT": str(output),
                "DEPLOY_STUDIO_OCI_CONFIG": str(config),
                "DEPLOY_STUDIO_OCI_KEY": str(key),
                "DEPLOY_STUDIO_ADB_WALLET": str(wallet),
                "DEPLOY_STUDIO_SOURCE_ARCHIVE": str(source_archive),
            }

            def fake_installer(arguments: list[str]) -> int:
                self.assertEqual(arguments[arguments.index("--admin-password") + 1], "AdminPass123")
                self.assertEqual(arguments[arguments.index("--wallet-password") + 1], "WalletPass123")
                self.assertEqual(arguments[arguments.index("--app-schema-password") + 1], "DeveloperPass123")
                self.assertEqual(arguments[arguments.index("--apex-user") + 1], "SELECT_AI_ADMIN")
                self.assertEqual(arguments[arguments.index("--model") + 1], "cohere.command-a-03-2025")
                schema_passwords_file = Path(arguments[arguments.index("--schema-passwords-file") + 1])
                self.assertEqual(
                    json.loads(schema_passwords_file.read_text(encoding="utf-8")),
                    {"SH": "SchemaPass123"},
                )
                if os.name != "nt":
                    self.assertEqual(stat.S_IMODE(schema_passwords_file.stat().st_mode), 0o600)
                self.assertNotIn("SchemaPass123", " ".join(arguments))
                apex_archive = Path(arguments[arguments.index("--apex-archive") + 1])
                self.assertEqual(apex_archive.read_text(encoding="utf-8"), "-- selected export")
                self.assertTrue((demo_data.DEMO_ROOT / "sh_demo" / "data" / "example.json").is_file())
                self.assertFalse((demo_data.DEMO_ROOT / "flexcube_demo").exists())
                self.assertFalse((demo_data.DEMO_ROOT.parent / "README.md").exists())
                output_dir = Path(arguments[arguments.index("--output-dir") + 1])
                output_dir.mkdir(parents=True)
                (output_dir / "deployment-report.md").write_text("# safe report\n", encoding="utf-8")
                return 0

            run_hook(environment, installer=fake_installer)

            rendered = output.read_text(encoding="utf-8")
            result = json.loads(rendered)
            self.assertEqual(result["artifacts"][0]["name"], "deployment-report.md")
            self.assertEqual(result["outputs"]["adb_db_name"], "SELECTAI")
            self.assertNotIn("AdminPass123", rendered)
            self.assertNotIn("WalletPass123", rendered)
            self.assertNotIn("DeveloperPass123", rendered)
            self.assertNotIn("SchemaPass123", rendered)

            merged_inputs, schema_passwords = _hook_inputs(
                json.loads(context.read_text(encoding="utf-8")),
                json.loads(secrets.read_text(encoding="utf-8")),
            )
            self.assertEqual(merged_inputs["autonomous_database_admin_password"], "AdminPass123")
            self.assertNotIn("select_ai_schema_passwords", merged_inputs)
            self.assertEqual(schema_passwords, {"SH": "SchemaPass123"})


if __name__ == "__main__":
    unittest.main()
