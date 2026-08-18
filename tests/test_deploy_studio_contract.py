import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployStudioContractTests(unittest.TestCase):
    def test_contract_points_to_existing_terraform_and_hook(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], 1)
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
                "select_ai_schema_passwords",
            ],
        )
        self.assertTrue(all((ROOT / path).exists() for path in contract["post_apply"]["include_paths"]))

    def test_declared_outputs_are_not_secrets(self) -> None:
        contract = json.loads((ROOT / "terraform" / "deploy-studio.json").read_text(encoding="utf-8"))
        forbidden = ("password", "private_key", "wallet_base64", "secret")

        self.assertFalse(any(token in name.lower() for name in contract["outputs"] for token in forbidden))

    def test_ask_oracle_v5001_export_matches_its_declared_official_hash(self) -> None:
        manifest = json.loads((ROOT / "apex" / "manifest.json").read_text(encoding="utf-8"))
        application = next(item for item in manifest["apps"] if item["id"] == "ask-oracle-chatbot-2026-08-06")
        export = ROOT / application["export_path"]

        self.assertEqual(export.stat().st_size, application["source"]["size_bytes"])
        self.assertEqual(hashlib.sha256(export.read_bytes()).hexdigest(), application["source"]["sha256"])


if __name__ == "__main__":
    unittest.main()
