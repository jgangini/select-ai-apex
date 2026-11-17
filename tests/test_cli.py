from pathlib import Path
import unittest

from test_support import repo_tempdir
from installer.cli import _existing_apex_application_id, main


def write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    config = tmp_path / "config"
    key = tmp_path / "key.pem"
    config.write_text(
        """
        [DEFAULT]
        user=ocid1.user.oc1..aaaa
        fingerprint=aa:bb
        tenancy=ocid1.tenancy.oc1..bbbb
        region=us-chicago-1
        """,
        encoding="utf-8",
    )
    key.write_text("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----", encoding="utf-8")
    return config, key


class CliTests(unittest.TestCase):
    def test_existing_apex_application_id_returns_exact_alias(self) -> None:
        class Cursor:
            def execute(self, *_args, **_kwargs):
                return None

            def fetchall(self):
                return [(100,)]

            def close(self):
                return None

        class Connection:
            def cursor(self):
                return Cursor()

        self.assertEqual(
            _existing_apex_application_id(Connection(), "SELECT_AI_APEX", "ASK_ORACLE"),
            100,
        )

    def test_plan_writes_expected_artifacts(self) -> None:
        with repo_tempdir() as tmp:
            tmp_path = Path(tmp)
            config, key = write_inputs(tmp_path)
            output = tmp_path / "outputs"

            exit_code = main(
                [
                    "plan",
                    "--mode",
                    "existing",
                    "--oci-config",
                    str(config),
                    "--oci-key",
                    str(key),
                    "--schemas",
                    "HR",
                    "--output-dir",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((output / "executed-steps.sql").exists())
            self.assertTrue((output / "deployment-report.md").exists())
            self.assertTrue((output / "secrets.json").exists())
