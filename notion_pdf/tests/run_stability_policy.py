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

from app import html_to_seamless_pdf, url_to_seamless_pdf


OUTPUT_DIR = ROOT / "output"
DEFAULT_PDF = OUTPUT_DIR / "stability_default_hybrid_text.pdf"
BANNER_PDF = OUTPUT_DIR / "stability_notion_banner_removed.pdf"
FINAL_TEXT = OUTPUT_DIR / "final_pdf_extracted_text.txt"
POLICY_SUMMARY = OUTPUT_DIR / "stability_policy_summary.txt"

BANNER_PHRASES = [
    "You're almost there",
    "sign up to start building in Notion today",
    "Sign up or login",
]


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def page_count(pdf_path: Path) -> int:
    return len(PdfReader(pdf_path).pages)


def sample_html(include_banner: bool = False) -> str:
    banner = ""
    if include_banner:
        banner = """
        <div role="banner" style="position:fixed; top:0; left:0; right:0; z-index:10000; background:#f5f5f5; padding:12px; border-bottom:1px solid #ddd;">
          You're almost there — sign up to start building in Notion today. Sign up or login
        </div>
        """
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Stability Policy Test</title>
  <style>
    body {{ font-family: Arial, "Apple SD Gothic Neo", sans-serif; color:#111; }}
    main {{ padding-top: 72px; }}
    h1 {{ font-size: 32px; }}
    p, li {{ font-size: 18px; line-height: 1.55; }}
    pre {{ font-family: Menlo, Consolas, monospace; font-size: 16px; white-space: pre-wrap; }}
  </style>
</head>
<body>
  {banner}
  <main>
    <h1>PDF 보기 품질 우선 테스트</h1>
    <p>종료 시 바로 프로비전 가능</p>
    <p>MasterVD2 Hyper-V HOST01 C:\\ClusterStorage PowerShell</p>
    <pre>Get-ChildItem -Path C:\\ClusterStorage</pre>
  </main>
</body>
</html>"""


def serve_html(html: str):
    temp_dir = Path(tempfile.mkdtemp(prefix="notion_pdf_banner_"))
    (temp_dir / "index.html").write_text(html, encoding="utf-8")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(temp_dir))
    server = socketserver.TCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/index.html"


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    default_result = html_to_seamless_pdf(
        sample_html(),
        str(DEFAULT_PDF),
        width=794,
        margin=40,
        scale=2,
    )
    default_text = extract_text(DEFAULT_PDF)

    server, url = serve_html(sample_html(include_banner=True))
    try:
        banner_result = url_to_seamless_pdf(
            url,
            str(BANNER_PDF),
            width=794,
            margin=40,
            scale=2,
        )
    finally:
        server.shutdown()
        server.server_close()

    banner_text = extract_text(BANNER_PDF)
    FINAL_TEXT.write_text(banner_text, encoding="utf-8")
    banner_debug_path = OUTPUT_DIR / "notion_banner_cleanup.json"
    banner_debug = banner_debug_path.read_text(encoding="utf-8") if banner_debug_path.exists() else ""
    banner_in_text = [phrase for phrase in BANNER_PHRASES if phrase in banner_text]
    banner_remaining_debug = [phrase for phrase in BANNER_PHRASES if phrase in banner_debug and '"remaining_banner_text": []' not in banner_debug]

    lines = [
        f"DEFAULT_MODE={default_result['text_layer_mode']}",
        f"DEFAULT_STATUS={default_result['text_layer_status']}",
        f"DEFAULT_PAGES={page_count(DEFAULT_PDF)}",
        f"DEFAULT_EXTRACTED_CHARS={len(default_text.strip())}",
        f"BANNER_PAGES={page_count(BANNER_PDF)}",
        f"BANNER_EXTRACTED_CHARS={len(banner_text.strip())}",
        f"BANNER_TEXT_PRESENT={banner_in_text}",
        f"BANNER_DEBUG_PATH={banner_debug_path}",
        f"BANNER_DEBUG_REMAINING_PRESENT={banner_remaining_debug}",
        f"BANNER_PDF={BANNER_PDF}",
        f"FINAL_TEXT={FINAL_TEXT}",
    ]
    POLICY_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(POLICY_SUMMARY.read_text(encoding="utf-8"))

    if default_result["text_layer_mode"] != "hybrid":
        return 1
    if default_result["text_layer_status"] not in ("applied", "partial"):
        return 1
    if page_count(DEFAULT_PDF) != 1 or page_count(BANNER_PDF) != 1:
        return 1
    if "종료 시 바로 프로비전 가능" not in default_text:
        return 1
    if banner_in_text:
        return 1
    if banner_debug_path.exists() and '"removed_count": 0' in banner_debug:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
