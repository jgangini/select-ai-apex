from pathlib import Path
import unittest

from test_support import repo_tempdir
from installer.cli import main


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
