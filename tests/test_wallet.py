import zipfile
from pathlib import Path
import unittest

from test_support import repo_tempdir
from installer.wallet import list_wallet_dsn_aliases


class WalletTests(unittest.TestCase):
    def test_list_wallet_dsn_aliases(self) -> None:
        with repo_tempdir() as tmp:
            wallet = Path(tmp) / "wallet.zip"
            with zipfile.ZipFile(wallet, "w") as archive:
                archive.writestr(
                    "tnsnames.ora",
                    """
                    selectai_low =
                      (DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)))

                    selectai_high=(DESCRIPTION=(ADDRESS=(PROTOCOL=tcps)))
                    # ignored = value
                    """,
                )

            self.assertEqual(list_wallet_dsn_aliases(wallet), ["selectai_high", "selectai_low"])
