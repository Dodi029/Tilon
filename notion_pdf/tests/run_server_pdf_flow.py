import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("PORT", "5055"))
BASE_URL = f"http://127.0.0.1:{PORT}"


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


def build_sample_html() -> Path:
    html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Server flow PDF test</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #111; }}
    .block {{ height: 260px; border-bottom: 1px solid #ccc; padding: 12px; }}
  </style>
</head>
<body>
  <h1>Server flow PDF test</h1>
  {blocks}
  <p id="last">LAST CONTENT - this line must be included in the full-page capture.</p>
</body>
</html>
""".format(
        blocks="\n".join(f"<div class='block'>Block {i}</div>" for i in range(35))
    )
    sample_path = Path(tempfile.gettempdir()) / "notion_pdf_server_flow_sample.html"
    sample_path.write_text(html, encoding="utf-8")
    return sample_path


def create_pdf(sample_path: Path) -> tuple[str, bytes, dict]:
    with sample_path.open("rb") as fp:
        response = requests.post(
            f"{BASE_URL}/convert/file",
            files={"file": ("server-flow.html", fp, "text/html")},
            data={"width": "794", "margin": "40", "ocr": "0"},
            timeout=10,
        )
    response.raise_for_status()
    job_id = response.json()["job_id"]

    deadline = time.time() + 180
    while time.time() < deadline:
        status_response = requests.get(f"{BASE_URL}/job/{job_id}", timeout=30)
        status_response.raise_for_status()
        status = status_response.json()
        if status["status"] == "done":
            pdf_response = requests.get(f"{BASE_URL}/download/{job_id}", timeout=15)
            pdf_response.raise_for_status()
            return job_id, pdf_response.content, status
        if status["status"] == "error":
            raise RuntimeError(status.get("error", "PDF job failed"))
        time.sleep(1)
    raise RuntimeError(f"PDF job timed out: {job_id}")


def verify_pdf(pdf_bytes: bytes, status: dict) -> Path:
    output_path = Path(tempfile.gettempdir()) / "notion_pdf_server_flow_result.pdf"
    output_path.write_bytes(pdf_bytes)
    reader = PdfReader(output_path)
    if len(reader.pages) != 1:
        raise AssertionError(f"Expected 1 page, got {len(reader.pages)}")

    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    if height <= width:
        raise AssertionError(f"Expected tall single-page PDF, got {width}x{height}")
    if status["height_difference"] > status["allowed_tolerance"]:
        raise AssertionError(
            f"Screenshot height difference exceeds tolerance: DIFF={status['height_difference']}, "
            f"TOLERANCE={status['allowed_tolerance']}"
        )
    if status["image_height"] + status["allowed_tolerance"] < status["content_box_bottom"]:
        raise AssertionError(
            f"Cropped image does not include the measured content bottom: PNG={status['image_height']}, "
            f"CONTENT_BOX_BOTTOM={status['content_box_bottom']}, TOLERANCE={status['allowed_tolerance']}"
        )
    if abs(status["left_margin_px"] - status["right_margin_px"]) > 1:
        raise AssertionError(
            f"Expected symmetric side margins, got L={status['left_margin_px']}, R={status['right_margin_px']}"
        )
    expected_pdf_height = status["image_height"] * (794 / status["image_width"])
    if abs(height - expected_pdf_height) > 1:
        raise AssertionError(
            f"PDF height is not based on final image size: PDF={height}, EXPECTED={expected_pdf_height}"
        )
    if status["pdf_image_x"] != 0:
        raise AssertionError(f"Expected image x=0 because image width equals PDF width, got {status['pdf_image_x']}")
    if output_path.stat().st_size <= 0:
        raise AssertionError("PDF file is empty")
    return output_path


def main() -> int:
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
        sample_path = build_sample_html()
        job_id, pdf_bytes, status = create_pdf(sample_path)
        output_path = verify_pdf(pdf_bytes, status)
        pages = len(PdfReader(output_path).pages)
        print(f"SERVER_URL={BASE_URL}")
        print(f"JOB_ID={job_id}")
        print(f"PDF={output_path}")
        print(f"DOM_SCROLL_HEIGHT={status['dom_scroll_height']}")
        print(f"BODY_SCROLL_HEIGHT={status['body_scroll_height']}")
        print(f"CONTENT_WRAPPER_SCROLL_HEIGHT={status['content_wrapper_scroll_height']}")
        print(f"MAX_ELEMENT_BOTTOM={status['max_element_bottom']}")
        print(f"EXPECTED_HEIGHT={status['expected_height']}")
        print(f"SCREENSHOT_PNG_HEIGHT={status['original_image_height']}")
        print(f"HEIGHT_DIFFERENCE={status['height_difference']}")
        print(f"ALLOWED_TOLERANCE={status['allowed_tolerance']}")
        print(f"ORIGINAL_SCREENSHOT_PNG={status['original_image_width']}x{status['original_image_height']}")
        print(f"CONTENT_BOUNDING_BOX=left:{status['content_box_left']},right:{status['content_box_right']},bottom:{status['pixel_content_bottom']}")
        print(f"CROPPED_IMAGE={status['cropped_image_width']}x{status['cropped_image_height']}")
        print(f"REMOVED_BOTTOM_MARGIN_PX={status['removed_bottom_margin_px']}")
        print(f"LEFT_MARGIN_BEFORE_PX={status['left_margin_before_px']}")
        print(f"RIGHT_MARGIN_BEFORE_PX={status['right_margin_before_px']}")
        print(f"LEFT_MARGIN_PX={status['left_margin_px']}")
        print(f"RIGHT_MARGIN_PX={status['right_margin_px']}")
        print(f"LEFT_MARGIN_AFTER_PX={status['left_margin_after_px']}")
        print(f"RIGHT_MARGIN_AFTER_PX={status['right_margin_after_px']}")
        print(f"PAGES={pages}")
        print(f"PDF_PAGE_SIZE={status['pdf_page_width']}x{status['pdf_page_height']}")
        print(f"PDF_IMAGE_X={status['pdf_image_x']}")
        print(f"PDF_IMAGE_PLACEMENT={status['pdf_image_placement']}")
        print(f"SCALE={status['scale']}")
        print(f"OCR_STATUS={status['ocr_status']}")
        print(f"PDF_FILE_SIZE={status['pdf_file_size']}")
        print(f"DEBUG_PNG={status['debug_png_path']}")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    raise SystemExit(main())
