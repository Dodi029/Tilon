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

from app import PDF_WIDTH_PX, html_to_seamless_pdf, url_to_seamless_pdf


OUTPUT_DIR = ROOT / "output"
REPORT_PATH = OUTPUT_DIR / "text_layer_quality_report.md"
COMPARE_TEXT = {
    "none": OUTPUT_DIR / "compare_no_text.txt",
    "ocr": OUTPUT_DIR / "compare_ocr.txt",
    "dom": OUTPUT_DIR / "compare_dom.txt",
    "hybrid": OUTPUT_DIR / "compare_dom_ocr.txt",
}
PORT = int(os.environ.get("QUALITY_PORT", "5075"))
BASE_URL = f"http://127.0.0.1:{PORT}"

MODES = ["none", "ocr", "dom", "hybrid"]
REQUIRED_TEXT = [
    "종료 시 바로 프로비전 가능",
    "MasterVD2",
    "Hyper-V",
    "C:\\ClusterStorage",
    "PowerShell",
]
STRICT_TEXT = [
    "ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능",
    "처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요",
    "MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터",
    "C:\\ClusterStorage\\Volume1\\MasterVD2",
]


def mixed_html(repeat: int = 5) -> str:
    blocks = []
    for index in range(repeat):
        blocks.append(
            f"""
            <section>
              <h2>HOST01 운영 점검 {index}</h2>
              <p>ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능</p>
              <p>처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요</p>
              <ul>
                <li>MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터</li>
                <li>PowerShell 명령어와 Windows 경로 복사 검증</li>
              </ul>
              <pre>C:\\ClusterStorage\\Volume1\\MasterVD2
PowerShell
$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py
Get-VM -Name MasterVD2 | Select-Object VMName, State</pre>
            </section>
            """
        )
    return base_html("한글 영문 경로 명령어 혼합 샘플", "\n".join(blocks))


def short_html() -> str:
    return base_html(
        "짧은 HTML 샘플",
        """
        <h2>MasterVD2 short validation</h2>
        <p>종료 시 바로 프로비전 가능</p>
        <p>Hyper-V HOST01 PowerShell C:\\ClusterStorage\\Volume1\\MasterVD2</p>
        <pre>PowerShell
Get-ChildItem -Path C:\\ClusterStorage</pre>
        """,
    )


def base_html(title: str, body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{
      font-family: Arial, "Apple SD Gothic Neo", sans-serif;
      color: #111;
      background: #fff;
      line-height: 1.55;
    }}
    h1 {{ font-size: 34px; }}
    h2 {{ font-size: 24px; margin-top: 28px; }}
    p, li {{ font-size: 18px; }}
    section {{ padding: 18px 0; border-bottom: 1px solid #ddd; }}
    pre {{
      font-family: Menlo, Consolas, "Courier New", monospace;
      font-size: 16px;
      line-height: 1.45;
      white-space: pre-wrap;
      border: 1px solid #222;
      padding: 14px;
    }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {body}
</body>
</html>"""


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def pdf_pages(pdf_path: Path) -> int:
    return len(PdfReader(pdf_path).pages)


def analyze_text(text: str) -> dict:
    return {
        "chars": len(text.strip()),
        "required": {target: target in text for target in REQUIRED_TEXT},
        "strict": {target: target in text for target in STRICT_TEXT},
        "broken": any(
            marker in text
            for marker in [
                "Mas종료",
                "Maste종료",
                "Hyper-V에서 Mas종료",
                "프로비전 가 능",
                "C: \\",
            ]
        ),
    }


def append_compare_text(mode: str, sample: str, text: str) -> None:
    with COMPARE_TEXT[mode].open("a", encoding="utf-8") as fp:
        fp.write(f"\n\n===== {sample} / {mode} =====\n")
        fp.write(text)
        fp.write("\n")


def run_direct_sample(sample_name: str, html: str) -> list[dict]:
    rows = []
    for mode in MODES:
        pdf_path = OUTPUT_DIR / f"quality_{sample_name}_{mode}.pdf"
        result = html_to_seamless_pdf(
            html,
            str(pdf_path),
            width=PDF_WIDTH_PX,
            margin=40,
            scale=3,
            ocr=mode != "none",
            text_layer_mode=mode,
        )
        text = extract_text(pdf_path)
        append_compare_text(mode, sample_name, text)
        rows.append({
            "sample": sample_name,
            "mode": mode,
            "pages": pdf_pages(pdf_path),
            "pdf": str(pdf_path),
            **analyze_text(text),
            "text_layer_status": result.get("text_layer_status", result.get("ocr_status")),
            "ocr_status": result.get("ocr_status"),
            "dom_items": result.get("dom_text_layer_items", 0),
            "ocr_words": result.get("ocr_inserted_words", 0),
        })
    return rows


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


def run_html_upload_sample(html: str) -> list[dict]:
    sample_path = Path(tempfile.gettempdir()) / "text_layer_quality_upload.html"
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
    rows = []
    try:
        wait_for_server()
        for mode in MODES:
            with sample_path.open("rb") as fp:
                response = requests.post(
                    f"{BASE_URL}/convert/file",
                    files={"file": ("quality-upload.html", fp, "text/html")},
                    data={
                        "width": "794",
                        "margin": "40",
                        "scale": "3",
                        "text_layer_mode": mode,
                        "ocr": "1" if mode != "none" else "0",
                    },
                    timeout=20,
                )
            response.raise_for_status()
            job_id = response.json()["job_id"]
            deadline = time.time() + 240
            while time.time() < deadline:
                status_response = requests.get(f"{BASE_URL}/job/{job_id}", timeout=30)
                status_response.raise_for_status()
                status = status_response.json()
                if status["status"] == "done":
                    pdf_response = requests.get(f"{BASE_URL}/download/{job_id}", timeout=30)
                    pdf_response.raise_for_status()
                    pdf_path = OUTPUT_DIR / f"quality_html_upload_{mode}.pdf"
                    pdf_path.write_bytes(pdf_response.content)
                    text = extract_text(pdf_path)
                    append_compare_text(mode, "html_upload", text)
                    rows.append({
                        "sample": "html_upload",
                        "mode": mode,
                        "pages": pdf_pages(pdf_path),
                        "pdf": str(pdf_path),
                        **analyze_text(text),
                        "text_layer_status": status.get("text_layer_status", status.get("ocr_status")),
                        "ocr_status": status.get("ocr_status"),
                        "dom_items": status.get("dom_text_layer_items", 0),
                        "ocr_words": status.get("ocr_inserted_words", 0),
                    })
                    break
                if status["status"] == "error":
                    raise RuntimeError(status.get("error", "PDF job failed"))
                time.sleep(1)
            else:
                raise RuntimeError(f"PDF job timed out: {job_id}")
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    return rows


def run_current_notion_url() -> list[dict]:
    url = os.environ.get("CURRENT_NOTION_URL", "").strip()
    if not url:
        return []
    rows = []
    for mode in MODES:
        pdf_path = OUTPUT_DIR / f"quality_current_notion_{mode}.pdf"
        result = url_to_seamless_pdf(
            url,
            str(pdf_path),
            width=PDF_WIDTH_PX,
            margin=40,
            scale=3,
            ocr=mode != "none",
            text_layer_mode=mode,
        )
        text = extract_text(pdf_path)
        append_compare_text(mode, "current_notion_url", text)
        rows.append({
            "sample": "current_notion_url",
            "mode": mode,
            "pages": pdf_pages(pdf_path),
            "pdf": str(pdf_path),
            **analyze_text(text),
            "text_layer_status": result.get("text_layer_status", result.get("ocr_status")),
            "ocr_status": result.get("ocr_status"),
            "dom_items": result.get("dom_text_layer_items", 0),
            "ocr_words": result.get("ocr_inserted_words", 0),
        })
    return rows


def mode_score(row: dict) -> int:
    return (
        sum(1 for ok in row["required"].values() if ok) * 10
        + sum(1 for ok in row["strict"].values() if ok) * 20
        - (30 if row["broken"] else 0)
    )


def write_report(rows: list[dict], notion_skipped: bool) -> None:
    lines = [
        "# Text Layer Quality Report",
        "",
        "## Summary",
        "",
        "- v3.0 대비 현재 변경사항을 비교하기 위해 none/OCR/DOM/DOM+OCR 네 모드를 같은 샘플에 적용했다.",
        "- 단순 글자 수가 아니라 필수 문구 exact match와 섞임 marker를 함께 판단했다.",
        "- 현재 Notion URL 테스트는 `CURRENT_NOTION_URL` 환경변수가 없으면 실행하지 않는다.",
        "",
        "## Results",
        "",
        "| sample | mode | pages | chars | required | strict | broken | status | dom_items | ocr_words |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |",
    ]
    for row in rows:
        required_count = sum(1 for ok in row["required"].values() if ok)
        strict_count = sum(1 for ok in row["strict"].values() if ok)
        lines.append(
            f"| {row['sample']} | {row['mode']} | {row['pages']} | {row['chars']} | "
            f"{required_count}/{len(REQUIRED_TEXT)} | {strict_count}/{len(STRICT_TEXT)} | "
            f"{'yes' if row['broken'] else 'no'} | {row['text_layer_status']} | "
            f"{row['dom_items']} | {row['ocr_words']} |"
        )
    lines.extend([
        "",
        "## Required Text Checks",
        "",
    ])
    for row in rows:
        lines.append(f"### {row['sample']} / {row['mode']}")
        for target, ok in row["required"].items():
            lines.append(f"- {target}: {'OK' if ok else 'MISS'}")
        for target, ok in row["strict"].items():
            lines.append(f"- {target}: {'OK' if ok else 'MISS'}")
        lines.append(f"- broken sentence marker: {'FAIL' if row['broken'] else 'OK'}")
        lines.append("")
    by_mode = {mode: [] for mode in MODES}
    for row in rows:
        by_mode[row["mode"]].append(mode_score(row))
    mode_average = {
        mode: (sum(scores) / len(scores) if scores else -999)
        for mode, scores in by_mode.items()
    }
    best_mode = max(mode_average, key=mode_average.get)
    lines.extend([
        "## Judgment",
        "",
        f"- mode average score: {mode_average}",
        f"- best measured mode: {best_mode}",
        "- default recommendation: hybrid. DOM text is preferred, OCR is used only as a supplemental layer for non-DOM/image text, and overlapping OCR should be excluded.",
    ])
    if notion_skipped:
        lines.append("- current Notion URL test: SKIPPED because CURRENT_NOTION_URL was not provided.")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    for path in COMPARE_TEXT.values():
        path.write_text("", encoding="utf-8")

    rows = []
    rows.extend(run_direct_sample("short_html", short_html()))
    rows.extend(run_direct_sample("mixed_html", mixed_html()))
    rows.extend(run_html_upload_sample(mixed_html(repeat=2)))
    notion_rows = run_current_notion_url()
    rows.extend(notion_rows)
    write_report(rows, notion_skipped=not bool(notion_rows))
    print(REPORT_PATH.read_text(encoding="utf-8"))

    failures = [
        row for row in rows
        if row["pages"] != 1 or row["broken"] or (row["mode"] != "none" and row["chars"] == 0)
    ]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
