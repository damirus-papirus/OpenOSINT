import unittest
from openosint.detector import detect
from openosint.validation import normalize_phone, validate_email


class DetectorTests(unittest.TestCase):
    def test_domain(self):
        self.assertEqual(detect("example.com"), "domain")

    def test_ip(self):
        self.assertEqual(detect("8.8.8.8"), "ip")

    def test_url(self):
        self.assertEqual(detect("https://example.com/path"), "url")

    def test_email(self):
        self.assertEqual(detect("a@example.com"), "email")

    def test_phone(self):
        self.assertEqual(detect("+1 202 555 0123"), "phone")

    def test_email_validation(self):
        self.assertTrue(validate_email("a@example.com")["valid_syntax"])

    def test_phone_normalization(self):
        self.assertEqual(normalize_phone("+1 (202) 555-0123")["normalized_digits"], "+12025550123")


if __name__ == "__main__":
    unittest.main()
