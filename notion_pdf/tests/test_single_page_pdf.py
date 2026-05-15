import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import PDF_WIDTH_PX, html_to_seamless_pdf


def count_pdf_pages(pdf_path: Path) -> int:
    return len(PdfReader(pdf_path).pages)


class SinglePagePdfTest(unittest.TestCase):
    def test_long_html_exports_as_one_page_pdf(self):
        output_path = Path(tempfile.gettempdir()) / "notion_pdf_single_page_test.pdf"
        html = """
        <!doctype html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: Arial, sans-serif; }}
            .block {{ height: 260px; border-bottom: 1px solid #ddd; }}
          </style>
        </head>
        <body>
          <h1>Single page PDF test</h1>
          {blocks}
          <p id="last">Last line must remain visible.</p>
        </body>
        </html>
        """.format(blocks="\n".join("<div class='block'>Block %d</div>" % i for i in range(35)))

        html_to_seamless_pdf(html, str(output_path), width=PDF_WIDTH_PX, margin=40)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)
        self.assertEqual(count_pdf_pages(output_path), 1)


if __name__ == "__main__":
    unittest.main()
