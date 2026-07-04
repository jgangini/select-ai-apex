import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeployStudioContractTests(unittest.TestCase):
    def test_contract_points_to_existing_terraform_and_hook(self) -> None:
        contract = json.loads((ROOT / "deploy-studio.json").read_text(encoding="utf-8"))

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
        contract = json.loads((ROOT / "deploy-studio.json").read_text(encoding="utf-8"))
        forbidden = ("password", "private_key", "wallet_base64", "secret")

        self.assertFalse(any(token in name.lower() for name in contract["outputs"] for token in forbidden))


if __name__ == "__main__":
    unittest.main()
