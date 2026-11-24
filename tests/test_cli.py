from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from test_support import repo_tempdir
from installer.apex_navigation import NAVIGATION_CSS, RAIL_NAVIGATION_CSS, apply_ask_oracle_navigation
from installer.cli import ApexReleaseError, _check_apex_release, _existing_apex_application_id, main
from installer.constants import DEFAULT_APEX_ARCHIVE


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
    def test_install_rejects_older_apex_before_running_setup_sql(self) -> None:
        connection = MagicMock()
        connection.cursor.return_value.__enter__.return_value.fetchone.return_value = ("26.1.5",)
        with repo_tempdir() as tmp:
            root = Path(tmp)
            config, key = write_inputs(root)
            with (
                patch("installer.cli.extract_wallet", return_value=root),
                patch("installer.cli.connect_with_wallet", return_value=connection),
                patch("installer.cli.execute_sql_text") as execute_sql,
            ):
                with self.assertRaisesRegex(ApexReleaseError, r"26\.1\.6.*26\.1\.5"):
                    main(
                        [
                            "install", "--mode", "existing", "--oci-config", str(config),
                            "--oci-key", str(key), "--schemas", "HR", "--dsn", "db_high",
                            "--wallet", str(root / "wallet.zip"), "--wallet-password", "test-wallet",
                            "--admin-password", "test-admin", "--output-dir", str(root / "outputs"),
                        ],
                        propagate_apex_release_error=True,
                    )
                execute_sql.assert_not_called()
        connection.close.assert_called_once()

    def test_release_check_accepts_equivalent_and_later_apex_versions(self) -> None:
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        for current in ("26.1.6", "26.1.6.00.00", "26.1.10", "26.2.0"):
            with self.subTest(current=current):
                cursor.fetchone.return_value = (current,)
                _check_apex_release(connection, DEFAULT_APEX_ARCHIVE)

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

    def test_ask_oracle_navigation_appends_once_to_the_existing_stylesheet(self) -> None:
        original = b".custom-left-menu { position: fixed; }"
        expected = original + NAVIGATION_CSS + RAIL_NAVIGATION_CSS

        for current in (original, original + NAVIGATION_CSS):
            with self.subTest(has_header_style=NAVIGATION_CSS in current):
                connection = MagicMock()
                cursor = connection.cursor.return_value.__enter__.return_value
                cursor.fetchone.side_effect = [
                    (7, "text/css", "utf-8", SimpleNamespace(read=lambda: current)),
                    (7, "text/css", "utf-8", SimpleNamespace(read=lambda: expected)),
                ]
                with patch.dict(sys.modules, {"oracledb": SimpleNamespace(DB_TYPE_BLOB=object())}):
                    self.assertTrue(apply_ask_oracle_navigation(connection, "WORKSPACE", 100))
                    self.assertFalse(apply_ask_oracle_navigation(connection, "WORKSPACE", 100))

                write, = [call for call in cursor.execute.call_args_list if "content" in call.kwargs]
                self.assertEqual(write.kwargs["file_id"], 7)
                self.assertEqual(write.kwargs["application_id"], 100)
                self.assertEqual(write.kwargs["content"], expected)
                connection.commit.assert_called_once()

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
            self.assertIn("us-chicago-1", (output / "deployment-report.md").read_text(encoding="utf-8"))

    def test_plan_uses_effective_region_for_select_ai_and_terraform(self) -> None:
        with repo_tempdir() as tmp:
            tmp_path = Path(tmp)
            config, key = write_inputs(tmp_path)
            output = tmp_path / "outputs"

            exit_code = main(
                [
                    "plan",
                    "--mode",
                    "new",
                    "--oci-config",
                    str(config),
                    "--oci-key",
                    str(key),
                    "--region",
                    "us-ashburn-1",
                    "--schemas",
                    "SH_DEMO",
                    "--output-dir",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn('"region": "us-ashburn-1"', (output / "02_select_ai_profile.sql").read_text(encoding="utf-8"))
            self.assertIn('"region": "us-ashburn-1"', (output / "terraform.tfvars.json").read_text(encoding="utf-8"))
