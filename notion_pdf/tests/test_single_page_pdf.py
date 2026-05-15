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
    def make_long_html(self, blocks_count: int = 35) -> str:
        return """
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
        """.format(blocks="\n".join("<div class='block'>Block %d</div>" % i for i in range(blocks_count)))

    def test_long_html_exports_as_one_page_pdf(self):
        output_path = Path(tempfile.gettempdir()) / "notion_pdf_single_page_test.pdf"
        html = self.make_long_html()

        result = html_to_seamless_pdf(html, str(output_path), width=PDF_WIDTH_PX, margin=40)

        self.assertTrue(output_path.exists())
        self.assertGreater(output_path.stat().st_size, 0)
        self.assertEqual(count_pdf_pages(output_path), 1)
        self.assertEqual(result["pages"], 1)
        self.assertEqual(result["image_width"], PDF_WIDTH_PX)
        self.assertGreater(result["dom_scroll_height"], 9000)
        self.assertGreater(result["body_scroll_height"], 9000)
        self.assertGreater(result["max_element_bottom"], 9000)
        self.assertLessEqual(result["height_difference"], result["allowed_tolerance"])
        self.assertGreaterEqual(
            result["image_height"] + result["allowed_tolerance"],
            result["content_box_bottom"],
        )
        self.assertGreater(result["image_height"], 9000)
        self.assertGreater(result["removed_bottom_margin_px"], 0)
        self.assertLessEqual(abs(result["left_margin_px"] - result["right_margin_px"]), 1)
        self.assertTrue(Path(result["debug_png_path"]).exists())

        pdf_width, pdf_height = pdf_page_size(output_path)
        self.assertGreater(pdf_height, pdf_width)
        self.assertAlmostEqual(
            pdf_height / pdf_width,
            result["image_height"] / result["image_width"],
            delta=0.02,
        )
        self.assertAlmostEqual(
            pdf_height,
            result["image_height"] * (PDF_WIDTH_PX / result["image_width"]),
            delta=1,
        )
        self.assertEqual(result["pdf_image_x"], 0)

        print(f"DOM_SCROLL_HEIGHT={result['dom_scroll_height']}")
        print(f"BODY_SCROLL_HEIGHT={result['body_scroll_height']}")
        print(f"CONTENT_WRAPPER_SCROLL_HEIGHT={result['content_wrapper_scroll_height']}")
        print(f"MAX_ELEMENT_BOTTOM={result['max_element_bottom']}")
        print(f"EXPECTED_HEIGHT={result['expected_height']}")
        print(f"SCREENSHOT_PNG_HEIGHT={result['original_image_height']}")
        print(f"HEIGHT_DIFFERENCE={result['height_difference']}")
        print(f"ALLOWED_TOLERANCE={result['allowed_tolerance']}")
        print(f"ORIGINAL_SCREENSHOT_PNG={result['original_image_width']}x{result['original_image_height']}")
        print(f"CONTENT_BOUNDING_BOX=left:{result['content_box_left']},right:{result['content_box_right']},bottom:{result['pixel_content_bottom']}")
        print(f"CROPPED_IMAGE={result['cropped_image_width']}x{result['cropped_image_height']}")
        print(f"REMOVED_BOTTOM_MARGIN_PX={result['removed_bottom_margin_px']}")
        print(f"LEFT_MARGIN_BEFORE_PX={result['left_margin_before_px']}")
        print(f"RIGHT_MARGIN_BEFORE_PX={result['right_margin_before_px']}")
        print(f"LEFT_MARGIN_PX={result['left_margin_px']}")
        print(f"RIGHT_MARGIN_PX={result['right_margin_px']}")
        print(f"LEFT_MARGIN_AFTER_PX={result['left_margin_after_px']}")
        print(f"RIGHT_MARGIN_AFTER_PX={result['right_margin_after_px']}")
        print(f"PDF_PAGE_COUNT={result['pages']}")
        print(f"PDF_PAGE_SIZE={result['pdf_page_width']}x{result['pdf_page_height']}")
        print(f"PDF_IMAGE_X={result['pdf_image_x']}")
        print(f"PDF_IMAGE_PLACEMENT={result['pdf_image_placement']}")
        print(f"DEBUG_PNG={result['debug_png_path']}")

    def test_scale_2_uses_higher_resolution_image_but_keeps_pdf_width(self):
        html = self.make_long_html(blocks_count=12)
        scale1_path = Path(tempfile.gettempdir()) / "notion_pdf_scale_1_test.pdf"
        scale2_path = Path(tempfile.gettempdir()) / "notion_pdf_scale_2_test.pdf"

        scale1 = html_to_seamless_pdf(html, str(scale1_path), width=PDF_WIDTH_PX, margin=40, scale=1)
        scale2 = html_to_seamless_pdf(html, str(scale2_path), width=PDF_WIDTH_PX, margin=40, scale=2)

        self.assertEqual(count_pdf_pages(scale1_path), 1)
        self.assertEqual(count_pdf_pages(scale2_path), 1)
        self.assertEqual(scale1["image_width"], PDF_WIDTH_PX)
        self.assertEqual(scale2["image_width"], PDF_WIDTH_PX * 2)
        self.assertEqual(scale1["pdf_page_width"], PDF_WIDTH_PX)
        self.assertEqual(scale2["pdf_page_width"], PDF_WIDTH_PX)
        self.assertGreater(scale2["pdf_file_size"], scale1["pdf_file_size"])

        print(f"SCALE1_FINAL_IMAGE={scale1['image_width']}x{scale1['image_height']}")
        print(f"SCALE1_PDF_PAGE_SIZE={scale1['pdf_page_width']}x{scale1['pdf_page_height']}")
        print(f"SCALE1_FILE_SIZE={scale1['pdf_file_size']}")
        print(f"SCALE2_FINAL_IMAGE={scale2['image_width']}x{scale2['image_height']}")
        print(f"SCALE2_PDF_PAGE_SIZE={scale2['pdf_page_width']}x{scale2['pdf_page_height']}")
        print(f"SCALE2_FILE_SIZE={scale2['pdf_file_size']}")


if __name__ == "__main__":
    unittest.main()
