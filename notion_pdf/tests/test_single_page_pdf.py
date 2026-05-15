import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import PDF_WIDTH_PX, html_to_seamless_pdf


def count_pdf_pages(pdf_path: Path) -> int:
    return len(PdfReader(pdf_path).pages)


def pdf_page_size(pdf_path: Path) -> tuple[float, float]:
    page = PdfReader(pdf_path).pages[0]
    return float(page.mediabox.width), float(page.mediabox.height)


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

        result = html_to_seamless_pdf(html, str(output_path), width=PDF_WIDTH_PX, margin=40)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)
        self.assertEqual(count_pdf_pages(output_path), 1)
        self.assertEqual(result["pages"], 1)
        self.assertEqual(result["image_width"], PDF_WIDTH_PX)
        self.assertGreater(result["dom_scroll_height"], 9000)
        self.assertGreater(result["body_scroll_height"], 9000)
        self.assertGreater(result["max_element_bottom"], 9000)
        self.assertGreaterEqual(result["image_height"], result["capture_height"])
        self.assertGreater(result["image_height"], 9000)
        self.assertTrue(Path(result["debug_png_path"]).exists())

        pdf_width, pdf_height = pdf_page_size(output_path)
        self.assertGreater(pdf_height, pdf_width)
        self.assertAlmostEqual(
            pdf_height / pdf_width,
            result["image_height"] / result["image_width"],
            delta=0.02,
        )

        print(f"DOM_SCROLL_HEIGHT={result['dom_scroll_height']}")
        print(f"BODY_SCROLL_HEIGHT={result['body_scroll_height']}")
        print(f"CONTENT_WRAPPER_SCROLL_HEIGHT={result['content_wrapper_scroll_height']}")
        print(f"MAX_ELEMENT_BOTTOM={result['max_element_bottom']}")
        print(f"SCREENSHOT_PNG={result['image_width']}x{result['image_height']}")
        print(f"PDF_PAGE_COUNT={result['pages']}")
        print(f"PDF_PAGE_SIZE={result['pdf_page_width']}x{result['pdf_page_height']}")
        print(f"DEBUG_PNG={result['debug_png_path']}")


if __name__ == "__main__":
    unittest.main()
