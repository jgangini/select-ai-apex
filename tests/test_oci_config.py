import unittest

from installer.oci_config import parse_oci_config_text


class OciConfigTests(unittest.TestCase):
    def test_parse_default_oci_config(self) -> None:
        parsed = parse_oci_config_text(
            """
            [DEFAULT]
            user=ocid1.user.oc1..aaaa
            fingerprint=aa:bb
            tenancy=ocid1.tenancy.oc1..bbbb
            region=us-chicago-1
            key_file=/ignored/key.pem
            """
        )

        self.assertEqual(parsed.user, "ocid1.user.oc1..aaaa")
        self.assertEqual(parsed.fingerprint, "aa:bb")
        self.assertEqual(parsed.tenancy, "ocid1.tenancy.oc1..bbbb")
        self.assertEqual(parsed.region, "us-chicago-1")

    def test_parse_named_profile(self) -> None:
        parsed = parse_oci_config_text(
            """
            [DEFAULT]
            user=wrong
            fingerprint=wrong
            tenancy=wrong
            region=wrong
            [PROD]
            user=ocid1.user.oc1..prod
            fingerprint=11:22
            tenancy=ocid1.tenancy.oc1..prod
            region=sa-saopaulo-1
            """,
            profile="PROD",
        )

        self.assertTrue(parsed.user.endswith("prod"))
        self.assertEqual(parsed.region, "sa-saopaulo-1")
