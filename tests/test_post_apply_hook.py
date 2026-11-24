import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from deploy.hooks.post_apply import _apex_application_url, _application, _hook_inputs, _stage_source_assets, run_hook
from installer import demo_data
from installer.cli import ApexReleaseError


class PostApplyHookTests(unittest.TestCase):
    def test_apex_application_url_uses_workspace_and_alias(self) -> None:
        self.assertEqual(
            _apex_application_url(
                "https://example.invalid/ords/apex",
                "SELECT_AI_APEX_5002",
                "ASK_ORACLE",
            ),
            "https://example.invalid/ords/r/select_ai_apex_5002/ask_oracle/home",
        )

    def test_source_staging_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_archive = root / "source.zip"
            with zipfile.ZipFile(source_archive, "w") as archive:
                archive.writestr(f"select-ai-apex-deadbeef/../{_application()['export_path']}", "unsafe")

            with self.assertRaisesRegex(ValueError, "unsafe path"):
                _stage_source_assets(
                    source_archive,
                    root / "stage",
                    _application(),
                    "SH_DEMO",
                )

    def test_new_database_stages_ask_oracle_and_selected_demos(self) -> None:
        application = _application()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source_archive = root / "source.zip"
            with zipfile.ZipFile(source_archive, "w") as archive:
                archive.writestr(f"select-ai-apex-sha/{application['export_path']}", "Ask Oracle")
                archive.writestr("select-ai-apex-sha/data/sh_demo/data/example.json", "{}")
                archive.writestr("select-ai-apex-sha/data/flexcube_demo/data/example.json", "{}")

            stage_root = root / "stage"
            export = _stage_source_assets(source_archive, stage_root, application, "SH_DEMO,FLEXCUBE_DEMO")
            self.assertEqual(export.read_text(encoding="utf-8"), "Ask Oracle")
            self.assertEqual(list((stage_root / "apex").iterdir()), [export])
            self.assertTrue((stage_root / "data" / "sh_demo" / "data" / "example.json").is_file())
            self.assertTrue((stage_root / "data" / "flexcube_demo" / "data" / "example.json").is_file())

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
                        "region": "us-ashburn-1",
                        "inputs": {
                            "autonomous_database_mode": "existing",
                            "existing_autonomous_database_ocid": "ocid1.autonomousdatabase.oc1..example",
                            "autonomous_database_version": "26ai",
                            "autonomous_database_workload": "DW",
                            "select_ai_model": "cohere.command-a-03-2025",
                            "select_ai_grant_schemas": "SH",
                            "select_ai_apex_app_id": "ask-oracle-chatbot-2026-11-18",
                            "application_username": "SELECT_AI_ADMIN",
                            "autonomous_database_admin_password": "PublicAdminMustNotWin",
                            "autonomous_database_wallet_password": "PublicWalletMustNotWin",
                            "autonomous_database_developer_password": "PublicDeveloperMustNotWin",
                            "existing_select_ai_grant_schemas": "SH",
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
                            "autonomous_database_wallet_password": " WalletPass123 ",
                            "autonomous_database_developer_password": "DeveloperPass123",
                        },
                    }
                ),
                encoding="utf-8",
            )
            config.write_text("[DEFAULT]\nregion=us-chicago-1\n", encoding="utf-8")
            key.write_text("test-key", encoding="utf-8")
            wallet.write_bytes(b"test-wallet")
            with zipfile.ZipFile(source_archive, "w") as archive:
                archive.writestr(f"select-ai-apex-deadbeef/{_application()['export_path']}", "-- selected export")
                archive.writestr("select-ai-apex-deadbeef/apex/unused.sql", "-- other asset")
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
                self.assertEqual(arguments[arguments.index("--wallet-password") + 1], " WalletPass123 ")
                self.assertEqual(arguments[arguments.index("--app-schema-password") + 1], "DeveloperPass123")
                self.assertEqual(arguments[arguments.index("--apex-user") + 1], "SELECT_AI_ADMIN")
                self.assertEqual(arguments[arguments.index("--workspace") + 1], "SELECT_AI_APEX_5002")
                self.assertEqual(arguments[arguments.index("--app-schema") + 1], "SELECT_AI_APP_5002")
                self.assertEqual(arguments[arguments.index("--model") + 1], "cohere.command-a-03-2025")
                self.assertEqual(arguments[arguments.index("--region") + 1], "us-ashburn-1")
                self.assertFalse(any(argument.startswith("--schema-password") for argument in arguments))
                apex_archive = Path(arguments[arguments.index("--apex-archive") + 1])
                self.assertEqual(apex_archive.read_text(encoding="utf-8"), "-- selected export")
                self.assertFalse((demo_data.DEMO_ROOT / "sh_demo").exists())
                self.assertFalse((demo_data.DEMO_ROOT / "flexcube_demo").exists())
                self.assertFalse((demo_data.DEMO_ROOT.parent / "README.md").exists())
                output_dir = Path(arguments[arguments.index("--output-dir") + 1])
                output_dir.mkdir(parents=True)
                (output_dir / "deployment-report.md").write_text("# safe report\n", encoding="utf-8")
                return 0

            self.assertEqual(run_hook(environment, installer=fake_installer), 0)

            rendered = output.read_text(encoding="utf-8")
            result = json.loads(rendered)
            self.assertEqual(result["artifacts"][0]["name"], "deployment-report.md")
            self.assertEqual(result["outputs"]["adb_db_name"], "SELECTAI")
            self.assertEqual(
                result["outputs"]["application_url"],
                "https://example.invalid/ords/r/select_ai_apex_5002/ask_oracle/home",
            )
            self.assertNotIn("AdminPass123", rendered)
            self.assertNotIn("WalletPass123", rendered)
            self.assertNotIn("DeveloperPass123", rendered)

            def incompatible_installer(_arguments: list[str]) -> int:
                raise ApexReleaseError("Oracle APEX 26.1.6 or later is required.")

            self.assertEqual(run_hook(environment, installer=incompatible_installer), 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), {
                "events": [{"level": "error", "message": "Oracle APEX 26.1.6 or later is required."}],
            })

            merged_inputs = _hook_inputs(
                json.loads(context.read_text(encoding="utf-8")),
                json.loads(secrets.read_text(encoding="utf-8")),
            )
            self.assertEqual(merged_inputs["autonomous_database_admin_password"], "AdminPass123")
            self.assertEqual(merged_inputs["select_ai_grant_schemas"], "SH")


if __name__ == "__main__":
    unittest.main()
