import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from app import PDF_WIDTH_PX, html_to_seamless_pdf


class NotionPreprocessTests(unittest.TestCase):
    def test_expands_toggles_and_removes_public_banner(self):
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Arial, sans-serif; color: #111; }
    header[role="banner"] {
      position: sticky;
      top: 0;
      background: #fff3cd;
      padding: 16px;
      border-bottom: 1px solid #e5d28a;
    }
    .notion-toggle-content[hidden] { display: none; }
    .spacer { height: 1800px; border-top: 1px solid #ddd; }
  </style>
  <script>
    function toggleBlock(button) {
      const target = document.getElementById(button.getAttribute('aria-controls'));
      const expanded = button.getAttribute('aria-expanded') === 'true';
      button.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      target.hidden = expanded;
    }
  </script>
</head>
<body>
  <header role="banner">You're almost there - sign up to start building in Notion today. Sign up or login</header>
  <main class="notion-page-content">
    <h1>Toggle preprocess sample</h1>
    <section data-block-id="outer-toggle" class="notion-toggle-block">
      <button role="button" aria-expanded="false" aria-controls="outer-content" class="notion-toggle" onclick="toggleBlock(this)">▶ Outer toggle</button>
      <div id="outer-content" class="notion-toggle-content" hidden>
        <p>VISIBLE_AFTER_OUTER_TOGGLE_EXPANSION</p>
        <details>
          <summary>Nested details toggle</summary>
          <p>VISIBLE_AFTER_NESTED_DETAILS_EXPANSION</p>
        </details>
      </div>
    </section>
    <div class="spacer">LAST LINE AFTER TOGGLES</div>
  </main>
</body>
</html>"""
        output_path = Path(tempfile.gettempdir()) / "notion_pdf_toggle_preprocess_test.pdf"
        result = html_to_seamless_pdf(
            html,
            str(output_path),
            width=PDF_WIDTH_PX,
            margin=40,
            scale=1,
            ocr=False,
            text_layer_mode="dom",
            expand_toggles=True,
            remove_banners=True,
        )
        text = "\n".join((page.extract_text() or "") for page in PdfReader(output_path).pages)
        self.assertEqual(result["pages"], 1)
        self.assertIn("VISIBLE_AFTER_OUTER_TOGGLE_EXPANSION", text)
        self.assertIn("VISIBLE_AFTER_NESTED_DETAILS_EXPANSION", text)
        self.assertNotIn("You're almost there", text)
        self.assertNotIn("Sign up or login", text)


if __name__ == "__main__":
    unittest.main()
