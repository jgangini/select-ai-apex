import json
from pathlib import Path
import unittest

from test_support import repo_tempdir
from installer.cli import grant_source_schema_access, main, read_schema_passwords_file
from installer.models import DeploymentOptions
from installer.oci_config import OciConfig
from installer.sqlgen import render_plan
from installer.validators import ValidationError


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

    def test_existing_mode_grants_access_as_each_schema_owner_without_rendering_passwords(self) -> None:
        source_passwords = {"HR": "HrOwnerPass123", "SH": "ShOwnerPass123"}
        options = DeploymentOptions(
            mode="existing",
            oci_config=OciConfig(
                tenancy="ocid1.tenancy.oc1..aaaa",
                user="ocid1.user.oc1..bbbb",
                fingerprint="aa:bb",
                region="us-chicago-1",
            ),
            oci_private_key="test-key",
            schemas=["HR", "SH"],
            tables=[],
            wallet=Path("wallet.zip"),
            wallet_password="WalletPass123",
            dsn="selectai_low",
            source_schema_passwords=source_passwords,
        )
        connections = []
        executions: list[tuple[str, str]] = []

        class Connection:
            def __init__(self, user: str) -> None:
                self.user = user
                self.closed = False

            def close(self) -> None:
                self.closed = True

        def connector(**kwargs):
            connection = Connection(kwargs["user"])
            connections.append((connection, kwargs))
            return connection

        def executor(connection, sql: str) -> int:
            executions.append((connection.user, sql))
            return 1

        grant_source_schema_access(
            options,
            Path("wallet"),
            connector=connector,
            executor=executor,
        )

        self.assertEqual([kwargs["user"] for _, kwargs in connections], ["HR", "SH"])
        self.assertEqual(
            [kwargs["password"] for _, kwargs in connections],
            ["HrOwnerPass123", "ShOwnerPass123"],
        )
        self.assertTrue(all(kwargs["dsn"] == "selectai_low" for _, kwargs in connections))
        self.assertTrue(all(kwargs["wallet_dir"] == Path("wallet") for _, kwargs in connections))
        self.assertTrue(all(kwargs["wallet_password"] == "WalletPass123" for _, kwargs in connections))
        self.assertTrue(all(connection.closed for connection, _ in connections))
        self.assertEqual([user for user, _ in executions], ["HR", "SH"])
        self.assertTrue(all("user_objects" in sql for _, sql in executions))
        self.assertTrue(all("MATERIALIZED VIEW" in sql for _, sql in executions))
        self.assertTrue(all("TO SELECT_AI_APP" in sql for _, sql in executions))

        rendered = render_plan(options)
        safe_outputs = "\n".join(
            [rendered.report_markdown, rendered.executed_steps_sql, rendered.secrets_json]
        )
        for password in source_passwords.values():
            self.assertNotIn(password, repr(options))
            self.assertNotIn(password, safe_outputs)
            self.assertTrue(all(password not in sql for _, sql in executions))

    def test_schema_password_file_rejects_unselected_owner(self) -> None:
        with repo_tempdir() as tmp:
            path = Path(tmp) / "schema-passwords.json"
            path.write_text(json.dumps({"SALES": "OwnerPass123"}), encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "not selected: SALES"):
                read_schema_passwords_file(path, ["HR"])
