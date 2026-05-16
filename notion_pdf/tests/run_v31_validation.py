import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import html_to_seamless_pdf


OUTPUT_DIR = ROOT / "output"
SUMMARY_PATH = OUTPUT_DIR / "v31_validation_summary.txt"
HTML_UPLOAD_RESULT = OUTPUT_DIR / "v31_html_upload_result.pdf"
HTML_UPLOAD_TEXT = OUTPUT_DIR / "v31_html_upload_result.txt"
PORT = int(os.environ.get("V31_PORT", "5065"))
BASE_URL = f"http://127.0.0.1:{PORT}"

REQUIRED_TEXT = [
    "종료 시 바로 프로비전 가능",
    "MasterVD",
    "MasterVD2",
    "HOST01",
    "Hyper-V",
    "ClusterStorage",
]


def sample_html(repeat: int = 8) -> str:
    blocks = []
    for index in range(repeat):
        blocks.append(
            f"""
            <section class="block">
              <h2>Hyper-V 운영 점검 {index}</h2>
              <p>종료 시 바로 프로비전 가능 상태를 확인합니다.</p>
              <p>MasterVD와 MasterVD2는 HOST01에서 실행됩니다.</p>
              <p>스토리지 경로는 C:\\ClusterStorage\\Volume1\\MasterVD 입니다.</p>
              <ul>
                <li>MasterVD 상태 확인</li>
                <li>HOST01 리소스 확인</li>
              </ul>
              <pre>$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py
Get-VM -Name MasterVD | Select-Object VMName, State
python -m unittest discover -s tests</pre>
            </section>
            """
        )
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>v3.1 validation sample</title>
  <style>
    body {{ font-family: Arial, "Apple SD Gothic Neo", sans-serif; color: #111; }}
    .block {{ min-height: 360px; border-bottom: 1px solid #ddd; padding: 16px 0; }}
    h1 {{ font-size: 32px; }}
    h2 {{ font-size: 24px; }}
    p, li {{ font-size: 18px; line-height: 1.55; }}
    pre {{
      font-family: Menlo, Consolas, "Courier New", monospace;
      font-size: 15px;
      line-height: 1.45;
      white-space: pre-wrap;
      border: 1px solid #222;
      padding: 12px;
    }}
  </style>
</head>
<body>
  <h1>v3.1 DOM text layer validation</h1>
  {''.join(blocks)}
</body>
</html>"""


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def assert_pdf_result(pdf_path: Path, result: dict, expect_text: bool) -> str:
    reader = PdfReader(pdf_path)
    if len(reader.pages) != 1:
        raise AssertionError(f"{pdf_path} page count is {len(reader.pages)}")
    if abs(result["left_margin_after_px"] - result["right_margin_after_px"]) > 2:
        raise AssertionError(
            f"{pdf_path} side margins differ: {result['left_margin_after_px']} vs {result['right_margin_after_px']}"
        )
    if result["removed_bottom_margin_px"] < 0:
        raise AssertionError(f"{pdf_path} bottom crop is invalid")
    text = extract_text(pdf_path)
    if expect_text and not text.strip():
        raise AssertionError(f"{pdf_path} has no extractable text")
    return text


def wait_for_server(timeout_seconds: int = 30) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(BASE_URL, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"Server did not start at {BASE_URL}: {last_error}")


def run_upload_flow(html: str) -> tuple[str, str]:
    sample_path = Path(tempfile.gettempdir()) / "v31_upload_sample.html"
    sample_path.write_text(html, encoding="utf-8")
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["FLASK_DEBUG"] = "0"
    server = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server()
        with sample_path.open("rb") as fp:
            response = requests.post(
                f"{BASE_URL}/convert/file",
                files={"file": ("v31-upload.html", fp, "text/html")},
                data={"width": "794", "margin": "40", "scale": "2", "text_layer_mode": "dom"},
                timeout=15,
            )
        response.raise_for_status()
        job_id = response.json()["job_id"]
        deadline = time.time() + 180
        while time.time() < deadline:
            status_response = requests.get(f"{BASE_URL}/job/{job_id}", timeout=30)
            status_response.raise_for_status()
            status = status_response.json()
            if status["status"] == "done":
                pdf_response = requests.get(f"{BASE_URL}/download/{job_id}", timeout=30)
                pdf_response.raise_for_status()
                HTML_UPLOAD_RESULT.write_bytes(pdf_response.content)
                text = extract_text(HTML_UPLOAD_RESULT)
                HTML_UPLOAD_TEXT.write_text(text, encoding="utf-8")
                for target in REQUIRED_TEXT:
                    if target not in text:
                        raise AssertionError(f"HTML upload missing text: {target}")
                return job_id, text
            if status["status"] == "error":
                raise RuntimeError(status.get("error", "PDF job failed"))
            time.sleep(1)
        raise RuntimeError(f"PDF job timed out: {job_id}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    html = sample_html()
    cases = [
        ("width_a4", {"width": 794, "margin": 40, "scale": 2, "mode": "dom"}),
        ("width_letter", {"width": 816, "margin": 40, "scale": 2, "mode": "dom"}),
        ("width_a3", {"width": 1123, "margin": 40, "scale": 2, "mode": "dom"}),
        ("margin_small", {"width": 794, "margin": 20, "scale": 2, "mode": "dom"}),
        ("margin_normal", {"width": 794, "margin": 40, "scale": 2, "mode": "dom"}),
        ("margin_large", {"width": 794, "margin": 60, "scale": 2, "mode": "dom"}),
        ("scale_1", {"width": 794, "margin": 40, "scale": 1, "mode": "dom"}),
        ("scale_2", {"width": 794, "margin": 40, "scale": 2, "mode": "dom"}),
        ("scale_3", {"width": 794, "margin": 40, "scale": 3, "mode": "dom"}),
        ("layer_none", {"width": 794, "margin": 40, "scale": 2, "mode": "none"}),
        ("layer_ocr", {"width": 794, "margin": 40, "scale": 2, "mode": "ocr"}),
        ("layer_dom", {"width": 794, "margin": 40, "scale": 2, "mode": "dom"}),
        ("layer_hybrid", {"width": 794, "margin": 40, "scale": 2, "mode": "hybrid"}),
    ]
    lines = []
    for name, options in cases:
        pdf_path = OUTPUT_DIR / f"v31_{name}.pdf"
        result = html_to_seamless_pdf(
            html,
            str(pdf_path),
            width=options["width"],
            margin=options["margin"],
            scale=options["scale"],
            ocr=options["mode"] != "none",
            text_layer_mode=options["mode"],
        )
        text = assert_pdf_result(pdf_path, result, expect_text=options["mode"] != "none")
        if options["mode"] in ("dom", "hybrid"):
            for target in REQUIRED_TEXT:
                if target not in text:
                    raise AssertionError(f"{name} missing required text: {target}")
        lines.append(
            f"{name}: pages={result['pages']} image={result['image_width']}x{result['image_height']} "
            f"pdf={result['pdf_page_width']}x{result['pdf_page_height']} "
            f"margins={result['left_margin_after_px']}/{result['right_margin_after_px']} "
            f"removed_bottom={result['removed_bottom_margin_px']} text_chars={len(text.strip())} "
            f"mode={options['mode']}"
        )

    job_id, upload_text = run_upload_flow(html)
    lines.append(f"html_upload: job={job_id} pages=1 text_chars={len(upload_text.strip())} output={HTML_UPLOAD_RESULT}")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(SUMMARY_PATH.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
