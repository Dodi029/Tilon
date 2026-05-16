import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import PDF_WIDTH_PX, html_to_seamless_pdf


OUTPUT_DIR = ROOT / "output"
OCR_OFF_PDF = OUTPUT_DIR / "ocr_comparison_no_ocr.pdf"
OCR_ON_PDF = OUTPUT_DIR / "ocr_comparison_with_ocr.pdf"
OCR_OFF_TEXT = OUTPUT_DIR / "ocr_comparison_no_ocr.txt"
OCR_ON_TEXT = OUTPUT_DIR / "ocr_comparison_with_ocr.txt"

TARGETS = [
    "C:\\dev\\projects\\Tilon\\notion_pdf",
    "C:\\Users\\dylee\\AppData\\Local\\Temp\\notion_pdf",
    "$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py",
    "python -m unittest discover -s tests",
    "Get-ChildItem -Path C:\\dev\\projects\\Tilon -Recurse",
    "from pathlib import Path",
    "print(Path(r\"C:\\dev\\projects\\Tilon\\notion_pdf\"))",
]


def build_html() -> str:
    target_lines = "\n".join(TARGETS)
    repeated = "\n\n".join(
        [
            "Windows paths\n"
            "C:\\dev\\projects\\Tilon\\notion_pdf\n"
            "C:\\Users\\dylee\\AppData\\Local\\Temp\\notion_pdf",
            "PowerShell commands\n"
            "$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py\n"
            "python -m unittest discover -s tests\n"
            "Get-ChildItem -Path C:\\dev\\projects\\Tilon -Recurse",
            "Code block\n"
            "from pathlib import Path\n"
            "print(Path(r\"C:\\dev\\projects\\Tilon\\notion_pdf\"))",
        ]
        * 2
    )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>OCR comparison test</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      color: #111;
      background: #fff;
    }}
    h1 {{
      font-size: 34px;
      margin: 0 0 20px;
    }}
    .section {{
      margin: 0 0 22px;
    }}
    .label {{
      font-size: 22px;
      font-weight: 700;
      margin: 0 0 8px;
    }}
    pre {{
      font-family: Menlo, Consolas, "Courier New", monospace;
      font-size: 18px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: normal;
      margin: 0;
      padding: 18px;
      border: 2px solid #111;
      background: #fff;
    }}
  </style>
</head>
<body>
  <h1>OCR comparison sample</h1>
  <div class="section">
    <div class="label">Exact targets</div>
    <pre>{target_lines}</pre>
  </div>
  <div class="section">
    <div class="label">Repeated OCR targets</div>
    <pre>{repeated}</pre>
  </div>
</body>
</html>"""


def extract_text(pdf_path: Path, txt_path: Path) -> str:
    reader = PdfReader(pdf_path)
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    txt_path.write_text(text, encoding="utf-8")
    return text


def count_matches(text: str) -> dict[str, bool]:
    return {target: target in text for target in TARGETS}


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    html = build_html()

    no_ocr = html_to_seamless_pdf(
        html,
        str(OCR_OFF_PDF),
        width=PDF_WIDTH_PX,
        margin=40,
        scale=3,
        ocr=False,
    )
    with_ocr = html_to_seamless_pdf(
        html,
        str(OCR_ON_PDF),
        width=PDF_WIDTH_PX,
        margin=40,
        scale=3,
        ocr=True,
    )

    no_ocr_text = extract_text(OCR_OFF_PDF, OCR_OFF_TEXT)
    ocr_text = extract_text(OCR_ON_PDF, OCR_ON_TEXT)
    no_ocr_matches = count_matches(no_ocr_text)
    ocr_matches = count_matches(ocr_text)

    print(f"OCR_OFF_PDF={OCR_OFF_PDF}")
    print(f"OCR_ON_PDF={OCR_ON_PDF}")
    print(f"OCR_OFF_TEXT={OCR_OFF_TEXT}")
    print(f"OCR_ON_TEXT={OCR_ON_TEXT}")
    print(f"OCR_OFF_STATUS={no_ocr['ocr_status']}")
    print(f"OCR_ON_STATUS={with_ocr['ocr_status']}")
    print(f"OCR_ON_LANGUAGE={with_ocr['ocr_language']}")
    print(f"OCR_OFF_EXTRACTED_CHARS={len(no_ocr_text)}")
    print(f"OCR_ON_EXTRACTED_CHARS={len(ocr_text)}")
    print(f"OCR_OFF_PAGES={no_ocr['pages']}")
    print(f"OCR_ON_PAGES={with_ocr['pages']}")
    print(f"OCR_OFF_IMAGE={no_ocr['image_width']}x{no_ocr['image_height']}")
    print(f"OCR_ON_IMAGE={with_ocr['image_width']}x{with_ocr['image_height']}")
    print(f"OCR_OFF_PDF_SIZE={OCR_OFF_PDF.stat().st_size}")
    print(f"OCR_ON_PDF_SIZE={OCR_ON_PDF.stat().st_size}")
    for target in TARGETS:
        print(f"TARGET={target}")
        print(f"  NO_OCR_EXACT={no_ocr_matches[target]}")
        print(f"  OCR_EXACT={ocr_matches[target]}")

    if with_ocr["ocr_status"] != "applied":
        print(f"OCR_ERROR={with_ocr.get('ocr_error')}")
        return 1
    if len(ocr_text.strip()) == 0:
        print("OCR text extraction produced no text.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
