import tempfile
import unittest
from pathlib import Path

from openosint.report import make_report, save_html


class HtmlReportTests(unittest.TestCase):
    def test_html_escapes_untrusted_query(self):
        report = make_report("<script>alert(1)</script>", "domain")
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "report.html"
            save_html(report, target)
            html_text = target.read_text(encoding="utf-8")
        self.assertNotIn("<script>alert(1)</script>", html_text)
        self.assertIn("&lt;script&gt;", html_text)


if __name__ == "__main__":
    unittest.main()
