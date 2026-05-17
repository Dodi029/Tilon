import functools
import http.server
import socketserver
import sys
import tempfile
import threading
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import url_to_seamless_pdf


OUTPUT_DIR = ROOT / "output"
PDF_PATH = OUTPUT_DIR / "banner_text_validation.pdf"
TEXT_PATH = OUTPUT_DIR / "final_pdf_extracted_text.txt"

BANNER_TEXT = [
    "You're almost there",
    "sign up to start building in Notion today",
    "Sign up or login",
]

REQUIRED_TEXT = [
    "CenterPost에서 바라보는 MasterVD2의 위치는 운영서버들의",
    "위 과정으로 프로비전 속도 증가 및 백업 역할 수행",
    "종료 시 바로 프로비전 가능",
    "처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요",
    "MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터",
]


def build_html() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Banner and DOM text validation</title>
  <style>
    body { font-family: Arial, sans-serif; color: #111; margin: 0; }
    header { position: fixed; top: 0; left: 0; right: 0; z-index: 1000; background: #f7f7f7; border-bottom: 1px solid #ddd; padding: 12px 24px; }
    main { padding: 96px 48px 80px; }
    p, li { font-size: 18px; line-height: 1.55; }
    .spacer { height: 380px; border-bottom: 1px solid #ddd; }
    pre { font-size: 16px; line-height: 1.45; white-space: pre-wrap; }
  </style>
</head>
<body>
  <header role="banner">You're almost there - sign up to start building in Notion today. Sign up or login</header>
  <main>
    <h1>MasterVD2 검증 문서</h1>
    <p>CenterPost에서 바라보는 MasterVD2의 위치는 운영서버들의 중앙 백업 지점입니다.</p>
    <p>위 과정으로 프로비전 속도 증가 및 백업 역할 수행</p>
    <p>종료 시 바로 프로비전 가능</p>
    <p>처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요</p>
    <p>MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터</p>
    <pre>C:\\ClusterStorage\\Volume1\\MasterVD2
PowerShell
Get-VM -Name MasterVD2 | Select-Object VMName, State</pre>
    <div class="spacer">중간 본문 블록 1</div>
    <div class="spacer">중간 본문 블록 2</div>
    <p>LAST CONTENT - full height capture validation</p>
  </main>
</body>
</html>"""


def serve_html(html: str):
    temp_dir = Path(tempfile.mkdtemp(prefix="notion_pdf_banner_text_"))
    (temp_dir / "index.html").write_text(html, encoding="utf-8")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(temp_dir))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/index.html"


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    server, url = serve_html(build_html())
    try:
        result = url_to_seamless_pdf(
            url,
            str(PDF_PATH),
            width=794,
            margin=40,
            scale=2,
            ocr=True,
            text_layer_mode="hybrid",
        )
    finally:
        server.shutdown()
        server.server_close()

    text = extract_text(PDF_PATH)
    TEXT_PATH.write_text(text, encoding="utf-8")
    pages = len(PdfReader(PDF_PATH).pages)
    missing = [item for item in REQUIRED_TEXT if item not in text]
    banner_hits = [item for item in BANNER_TEXT if item in text]

    print(f"PDF={PDF_PATH}")
    print(f"FINAL_PDF_EXTRACTED_TEXT={TEXT_PATH}")
    print(f"PAGES={pages}")
    print(f"IMAGE={result['image_width']}x{result['image_height']}")
    print(f"TEXT_CHARS={len(text.strip())}")
    print(f"MISSING_REQUIRED={missing}")
    print(f"BANNER_TEXT_HITS={banner_hits}")
    print(f"REMOVED_BOTTOM_MARGIN_PX={result['removed_bottom_margin_px']}")
    print(f"LEFT_MARGIN_AFTER_PX={result['left_margin_after_px']}")
    print(f"RIGHT_MARGIN_AFTER_PX={result['right_margin_after_px']}")

    if pages != 1:
        return 1
    if missing or banner_hits:
        return 1
    if result["height_difference"] > result["allowed_tolerance"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
