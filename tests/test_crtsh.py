import unittest

from openosint.sources.crtsh import _valid_dns_name


class CertificateNameTests(unittest.TestCase):
    def test_accepts_normal_and_wildcard_normalized_names(self):
        self.assertTrue(_valid_dns_name("github.com"))
        self.assertTrue(_valid_dns_name("api.github.com"))

    def test_rejects_non_dns_strings(self):
        self.assertFalse(_valid_dns_name("github, inc."))
        self.assertFalse(_valid_dns_name("support@github.com"))
        self.assertFalse(_valid_dns_name("https://github.com/owner/repo"))
        self.assertFalse(_valid_dns_name("not a hostname"))


if __name__ == "__main__":
    unittest.main()
