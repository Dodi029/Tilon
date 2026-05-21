from flask import Flask, request, jsonify, send_file, render_template_string
import os, shutil, tempfile, time, threading
from datetime import datetime
from pathlib import Path

from werkzeug.utils import secure_filename

from db import get_conversion, init_db, list_recent_conversions, record_conversion

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "50")) * 1024 * 1024
ROOT_DIR = Path(__file__).resolve().parent
UPLOADS_FOLDER = ROOT_DIR / "uploads"
UPLOADS_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER = ROOT_DIR / "output"
OUTPUT_FOLDER.mkdir(exist_ok=True)
OUTPUT_PDF_FOLDER = OUTPUT_FOLDER / "pdf"
OUTPUT_PNG_FOLDER = OUTPUT_FOLDER / "png"
OUTPUT_TXT_FOLDER = OUTPUT_FOLDER / "txt"
DEBUG_OUTPUT_FOLDER = OUTPUT_FOLDER / "debug"
OUTPUT_TESTS_FOLDER = OUTPUT_FOLDER / "tests"
for folder in (OUTPUT_PDF_FOLDER, OUTPUT_PNG_FOLDER, OUTPUT_TXT_FOLDER, DEBUG_OUTPUT_FOLDER, OUTPUT_TESTS_FOLDER):
    folder.mkdir(parents=True, exist_ok=True)
LOG_DIR = ROOT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
ALLOWED_UPLOAD_EXTENSIONS = {"html", "htm", "zip", "pdf", "txt"}
try:
    init_db()
except Exception as exc:
    print(f"DB_INIT_ERROR={exc}")

HTML_PAGE = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Notion → PDF 변환기</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&family=Space+Mono:wght@400;700&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg: #0e0e0f;
    --surface: #18181b;
    --surface2: #232328;
    --border: #2e2e35;
    --accent: #7c6aff;
    --accent2: #a78bfa;
    --text: #f0f0f3;
    --muted: #8b8b9a;
    --success: #34d399;
    --error: #f87171;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Noto Sans KR', sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .grain {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
    opacity: 0.4;
  }

  .glow {
    position: fixed; top: -200px; left: 50%; transform: translateX(-50%);
    width: 600px; height: 400px;
    background: radial-gradient(ellipse, rgba(124,106,255,0.15) 0%, transparent 70%);
    pointer-events: none; z-index: 0;
  }

  .container {
    position: relative; z-index: 1;
    width: 100%; max-width: 640px;
  }

  .header {
    text-align: center;
    margin-bottom: 3rem;
    animation: fadeUp 0.6s ease both;
  }

  .logo {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.3em;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 1rem;
  }

  h1 {
    font-size: 2.5rem;
    font-weight: 700;
    line-height: 1.1;
    background: linear-gradient(135deg, #fff 0%, var(--accent2) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.75rem;
  }

  .subtitle {
    color: var(--muted);
    font-size: 0.95rem;
    line-height: 1.6;
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2rem;
    animation: fadeUp 0.6s ease 0.1s both;
  }

  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.75rem;
    background: var(--surface2);
    border-radius: 10px;
    padding: 4px;
  }

  .tab {
    flex: 1;
    padding: 0.6rem 1rem;
    border: none;
    border-radius: 7px;
    background: transparent;
    color: var(--muted);
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.2s;
    font-weight: 500;
  }

  .tab.active {
    background: var(--accent);
    color: #fff;
  }

  .panel { display: none; }
  .panel.active { display: block; }

  .label {
    display: block;
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--muted);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
  }

  .input-wrap {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
  }

  input[type="text"] {
    flex: 1;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 10px;
    color: var(--text);
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    padding: 0.75rem 1rem;
    outline: none;
    transition: border-color 0.2s;
  }

  input[type="text"]:focus { border-color: var(--accent); }
  input[type="text"]::placeholder { color: var(--muted); }

  .drop-zone {
    border: 2px dashed var(--border);
    border-radius: 10px;
    padding: 2.5rem 1rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s;
    margin-bottom: 1.25rem;
    position: relative;
  }

  .drop-zone:hover, .drop-zone.drag { border-color: var(--accent); background: rgba(124,106,255,0.05); }

  .drop-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .drop-text { color: var(--muted); font-size: 0.875rem; }
  .drop-text strong { color: var(--accent2); }

  #fileInput { display: none; }

  .file-name {
    display: none;
    background: var(--surface2);
    border-radius: 8px;
    padding: 0.6rem 1rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: var(--success);
    margin-bottom: 1.25rem;
    align-items: center;
    gap: 0.5rem;
  }
  .file-name.show { display: flex; }

  .options {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  .option-group label.label { margin-bottom: 0.4rem; }
  .option-help {
    color: var(--muted);
    font-size: 0.7rem;
    line-height: 1.35;
    margin-top: 0.35rem;
  }

  select {
    width: 100%;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 0.85rem;
    padding: 0.6rem 0.75rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.2s;
  }

  select:focus { border-color: var(--accent); }

  .btn {
    width: 100%;
    padding: 0.9rem;
    border: none;
    border-radius: 10px;
    background: var(--accent);
    color: #fff;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 1rem;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    position: relative;
    overflow: hidden;
  }

  .btn:hover { background: var(--accent2); transform: translateY(-1px); box-shadow: 0 8px 24px rgba(124,106,255,0.3); }
  .btn:active { transform: translateY(0); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }

  .progress {
    display: none;
    margin-top: 1.5rem;
  }
  .progress.show { display: block; }

  .progress-bar-wrap {
    background: var(--surface2);
    border-radius: 100px;
    height: 4px;
    overflow: hidden;
    margin-bottom: 0.75rem;
  }

  .progress-bar {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    border-radius: 100px;
    width: 0%;
    transition: width 0.4s ease;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { filter: brightness(1); }
    50% { filter: brightness(1.3); }
    100% { filter: brightness(1); }
  }

  .progress-text {
    font-size: 0.8rem;
    color: var(--muted);
    font-family: 'Space Mono', monospace;
    text-align: center;
  }

  .result {
    display: none;
    margin-top: 1.5rem;
    background: rgba(52,211,153,0.08);
    border: 1px solid rgba(52,211,153,0.25);
    border-radius: 10px;
    padding: 1.25rem;
    text-align: center;
  }
  .result.show { display: block; }
  .result.error { background: rgba(248,113,113,0.08); border-color: rgba(248,113,113,0.25); }

  .result-icon { font-size: 1.75rem; margin-bottom: 0.5rem; }
  .result-title { font-weight: 700; font-size: 1rem; margin-bottom: 0.35rem; }
  .result.show:not(.error) .result-title { color: var(--success); }
  .result.error .result-title { color: var(--error); }
  .result-sub { font-size: 0.8rem; color: var(--muted); margin-bottom: 1rem; }

  .btn-download {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.6rem 1.5rem;
    border-radius: 8px;
    background: var(--success);
    color: #000;
    font-weight: 700;
    font-size: 0.875rem;
    text-decoration: none;
    transition: all 0.2s;
  }

  .btn-download:hover { opacity: 0.85; transform: translateY(-1px); }

  .how-to {
    margin-top: 1.5rem;
    background: rgba(124,106,255,0.06);
    border: 1px solid rgba(124,106,255,0.15);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    animation: fadeUp 0.6s ease 0.2s both;
  }

  .how-to-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent2);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
  }

  .steps {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .step {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    font-size: 0.8rem;
    color: var(--muted);
    line-height: 1.5;
  }

  .step-num {
    flex-shrink: 0;
    width: 20px; height: 20px;
    border-radius: 50%;
    background: var(--surface2);
    border: 1px solid var(--border);
    display: flex; align-items: center; justify-content: center;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--accent);
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .notion-hint {
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 0.4rem;
    line-height: 1.5;
  }

  .notion-hint code {
    background: var(--surface2);
    padding: 0.1em 0.4em;
    border-radius: 4px;
    font-family: 'Space Mono', monospace;
    color: var(--accent2);
    font-size: 0.7rem;
  }
</style>
</head>
<body>
<div class="grain"></div>
<div class="glow"></div>

<div class="container">
  <div class="header">
    <div class="logo">✦ Notion Tools</div>
    <h1>페이지 분할 없는<br>PDF 변환기</h1>
    <p class="subtitle">Notion 페이지를 한 장으로 이어지는 PDF로<br>깔끔하게 변환해 드려요</p>
  </div>

  <div class="card">
    <div class="tabs">
      <button class="tab active" onclick="switchTab('url')">🔗 URL 입력</button>
      <button class="tab" onclick="switchTab('file')">📄 파일 업로드</button>
    </div>

    <!-- URL 탭 -->
    <div class="panel active" id="panel-url">
      <label class="label">Notion 페이지 URL</label>
      <div class="input-wrap">
        <input type="text" id="notionUrl" placeholder="https://www.notion.so/..." />
      </div>
      <p class="notion-hint">
        💡 Notion 페이지가 <strong>공개(Public)</strong>로 설정되어 있어야 해요.<br>
        페이지 우측 상단 <code>공유</code> → <code>웹에 게시</code>를 켜주세요.
      </p>
    </div>

    <!-- 파일 탭 -->
    <div class="panel" id="panel-file">
      <label class="label">HTML, PDF, ZIP 또는 TXT 파일</label>
      <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <div class="drop-icon">📂</div>
        <div class="drop-text">클릭하거나 <strong>파일을 여기에 드래그</strong>하세요<br><span style="font-size:0.75rem; margin-top:0.25rem; display:block">지원 형식: .html, .htm, .pdf, .zip, .txt</span></div>
      </div>
      <input type="file" id="fileInput" accept=".html,.htm,.pdf,.zip,.txt" onchange="handleFile(this)">
      <div class="file-name" id="fileName">
        <span>✓</span>
        <span id="fileNameText"></span>
      </div>
    </div>

    <div class="options">
      <div class="option-group">
        <label class="label">용지 너비</label>
        <select id="pageWidth">
          <option value="794">A4 (794px)</option>
          <option value="1123">A3 (1123px)</option>
          <option value="816">Letter (816px)</option>
          <option value="1200">넓게 (1200px)</option>
        </select>
      </div>
      <div class="option-group">
        <label class="label">여백</label>
        <select id="margin">
          <option value="40">보통 (40px)</option>
          <option value="20">좁게 (20px)</option>
          <option value="0">없음 (0px)</option>
          <option value="60">넓게 (60px)</option>
        </select>
      </div>
      <div class="option-group">
        <label class="label">화질</label>
        <select id="qualityScale">
          <option value="2">고화질 (2x)</option>
          <option value="1">보통 (1x)</option>
          <option value="3">최고화질 (3x)</option>
        </select>
      </div>
      <div class="option-group">
        <label class="label">텍스트 레이어</label>
        <select id="textLayerMode">
          <option value="hybrid">DOM + OCR</option>
          <option value="dom">DOM</option>
          <option value="ocr">OCR</option>
          <option value="none">없음</option>
        </select>
      </div>
      <div class="option-group">
        <label class="label">Notion 토글 자동 펼치기</label>
        <select id="expandToggles">
          <option value="1">켜짐</option>
          <option value="0">꺼짐</option>
        </select>
        <div class="option-help">PDF 변환 전 닫혀 있는 Notion 토글을 자동으로 펼쳐 내부 내용까지 포함합니다.</div>
      </div>
      <div class="option-group">
        <label class="label">Notion 상단 배너 제거</label>
        <select id="removeBanners">
          <option value="1">켜짐</option>
          <option value="0">꺼짐</option>
        </select>
        <div class="option-help">공개 Notion 페이지의 로그인/가입 안내 배너를 캡처에서 제외합니다.</div>
      </div>
    </div>

    <button class="btn" id="convertBtn" onclick="convert()">
      PDF 변환 시작
    </button>

    <div class="progress" id="progress">
      <div class="progress-bar-wrap">
        <div class="progress-bar" id="progressBar"></div>
      </div>
      <div class="progress-text" id="progressText">준비 중...</div>
    </div>

    <div class="result" id="result">
      <div class="result-icon" id="resultIcon"></div>
      <div class="result-title" id="resultTitle"></div>
      <div class="result-sub" id="resultSub"></div>
      <a id="downloadBtn" class="btn-download" href="#" download>
        ⬇ PDF 다운로드
      </a>
    </div>
  </div>

  <div class="how-to">
    <div class="how-to-title">사용 방법</div>
    <div class="steps">
      <div class="step"><div class="step-num">1</div><span>Notion 페이지를 <strong>웹에 게시</strong>하거나, HTML로 내보내기 하세요</span></div>
      <div class="step"><div class="step-num">2</div><span>URL을 붙여넣거나 HTML/PDF 파일을 업로드하세요</span></div>
      <div class="step"><div class="step-num">3</div><span>용지 너비와 여백을 설정하고 변환을 시작하세요</span></div>
      <div class="step"><div class="step-num">4</div><span>페이지 분할 없는 PDF를 다운로드하세요 🎉</span></div>
    </div>
  </div>
</div>

<script>
let currentTab = 'url';
let selectedFile = null;
let jobId = null;

function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', (tab==='url'&&i===0)||(tab==='file'&&i===1)));
  document.getElementById('panel-url').classList.toggle('active', tab==='url');
  document.getElementById('panel-file').classList.toggle('active', tab==='file');
  hideResult();
}

function handleFile(input) {
  const file = input.files[0];
  if (!file) return;
  selectedFile = file;
  document.getElementById('fileNameText').textContent = file.name;
  document.getElementById('fileName').classList.add('show');
}

const dz = document.getElementById('dropZone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('drag');
  const file = e.dataTransfer.files[0];
  if (file) { selectedFile = file; document.getElementById('fileNameText').textContent = file.name; document.getElementById('fileName').classList.add('show'); }
});

function hideResult() {
  document.getElementById('result').classList.remove('show','error');
  document.getElementById('progress').classList.remove('show');
}

function setProgress(pct, text) {
  document.getElementById('progress').classList.add('show');
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressText').textContent = text;
}

async function convert() {
  hideResult();
  const btn = document.getElementById('convertBtn');
  btn.disabled = true;

  const width = document.getElementById('pageWidth').value;
  const margin = document.getElementById('margin').value;
  const scaleEl = document.getElementById('qualityScale');
  const scale = scaleEl ? scaleEl.value : '2';
  const layerEl = document.getElementById('textLayerMode');
  const textLayerMode = layerEl ? layerEl.value : 'hybrid';
  const ocr = textLayerMode !== 'none';
  const expandTogglesEl = document.getElementById('expandToggles');
  const removeBannersEl = document.getElementById('removeBanners');
  const expandToggles = expandTogglesEl ? expandTogglesEl.value !== '0' : true;
  const removeBanners = removeBannersEl ? removeBannersEl.value !== '0' : true;

  try {
    let response;
    setProgress(10, '업로드 중...');

    if (currentTab === 'url') {
      const url = document.getElementById('notionUrl').value.trim();
      if (!url) { alert('URL을 입력해주세요.'); btn.disabled=false; return; }
      setProgress(20, 'URL 분석 중...');
      response = await fetch('/convert/url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ url, width: parseInt(width), margin: parseInt(margin), scale: parseInt(scale), text_layer_mode: textLayerMode, ocr, expand_toggles: expandToggles, remove_banners: removeBanners })
      });
    } else {
      if (!selectedFile) { alert('파일을 선택해주세요.'); btn.disabled=false; return; }
      setProgress(20, '파일 업로드 중...');
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('width', width);
      fd.append('margin', margin);
      fd.append('scale', scale);
      fd.append('ocr', ocr ? '1' : '0');
      fd.append('text_layer_mode', textLayerMode);
      fd.append('expand_toggles', expandToggles ? '1' : '0');
      fd.append('remove_banners', removeBanners ? '1' : '0');
      response = await fetch('/convert/file', { method: 'POST', body: fd });
    }

    setProgress(40, 'PDF 변환 중... (잠시 기다려주세요)');
    const data = await response.json();

    if (!response.ok || data.error) {
      throw new Error(data.error || '변환 실패');
    }

    // Poll for job completion
    jobId = data.job_id;
    await pollJob(jobId);

  } catch(e) {
    showError(e.message);
    btn.disabled = false;
  }
}

async function pollJob(id) {
  const btn = document.getElementById('convertBtn');
  let dots = 0;
  const msgs = ['페이지 렌더링 중...', 'CSS 적용 중...', 'PDF 생성 중...', '마무리 중...'];
  let msgIdx = 0;

  const interval = setInterval(async () => {
    dots++;
    if (dots % 5 === 0 && msgIdx < msgs.length - 1) msgIdx++;
    const pct = Math.min(40 + dots * 4, 90);
    setProgress(pct, msgs[msgIdx]);
  }, 800);

  try {
    const maxWait = 60;
    for (let i = 0; i < maxWait; i++) {
      await new Promise(r => setTimeout(r, 1000));
      const res = await fetch(`/job/${id}`);
      const data = await res.json();
      if (data.status === 'done') {
        clearInterval(interval);
        setProgress(100, '완료!');
        setTimeout(() => showSuccess(data.filename, id), 300);
        btn.disabled = false;
        return;
      }
      if (data.status === 'error') {
        clearInterval(interval);
        throw new Error(data.error || '변환 중 오류 발생');
      }
    }
    throw new Error('시간 초과 - 다시 시도해주세요');
  } catch(e) {
    clearInterval(interval);
    showError(e.message);
    btn.disabled = false;
  }
}

function showSuccess(filename, id) {
  const r = document.getElementById('result');
  r.classList.add('show');
  document.getElementById('resultIcon').textContent = '🎉';
  document.getElementById('resultTitle').textContent = '변환 완료!';
  document.getElementById('resultSub').textContent = filename;
  const dlBtn = document.getElementById('downloadBtn');
  dlBtn.href = `/download/${id}`;
  dlBtn.style.display = 'inline-flex';
}

function showError(msg) {
  const r = document.getElementById('result');
  r.classList.add('show','error');
  document.getElementById('resultIcon').textContent = '⚠️';
  document.getElementById('resultTitle').textContent = '변환 실패';
  document.getElementById('resultSub').textContent = msg;
  document.getElementById('downloadBtn').style.display = 'none';
  document.getElementById('progress').classList.remove('show');
}
</script>
</body>
</html>'''

# ─── Job store ───────────────────────────────────────────────
jobs = {}  # job_id -> {status, filename, path, error}
PDF_WIDTH_PX = 794
PDF_EXTRA_HEIGHT_PX = 200
PDF_MIN_BOTTOM_MARGIN_PX = 40
PDF_MIN_SIDE_MARGIN_PX = 40
PDF_HEIGHT_TOLERANCE_PX = 150
PDF_BACKGROUND_COLOR = (255, 255, 255)
PDF_OCR_LANGUAGE = os.environ.get("OCR_LANG", "kor+eng")
PDF_OCR_TIMEOUT_SECONDS = int(os.environ.get("OCR_TIMEOUT_SECONDS", "300"))
PDF_OCR_CHUNK_HEIGHT_PX = int(os.environ.get("OCR_CHUNK_HEIGHT_PX", "3000"))
PDF_OCR_CHUNK_OVERLAP_PX = int(os.environ.get("OCR_CHUNK_OVERLAP_PX", "80"))
PDF_OCR_MIN_TEXT_RATIO = float(os.environ.get("OCR_MIN_TEXT_RATIO", "0.0008"))
PDF_SCREENSHOT_CHUNK_HEIGHT_PX = int(os.environ.get("SCREENSHOT_CHUNK_HEIGHT_PX", "8000"))
PDF_SCREENSHOT_CHUNK_RETRIES = int(os.environ.get("SCREENSHOT_CHUNK_RETRIES", "3"))
PDF_RENDER_STABLE_TIMEOUT_MS = int(os.environ.get("PDF_RENDER_STABLE_TIMEOUT_MS", "45000"))

def make_job_id():
    import uuid
    return str(uuid.uuid4())[:8]

def parse_bool(value, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("0", "false", "no", "off")

def normalize_text_layer_mode(value=None, ocr_enabled: bool = True) -> str:
    mode = (value or "").strip().lower()
    if mode in ("none", "ocr", "dom", "hybrid"):
        return mode
    return "hybrid" if ocr_enabled else "none"

def make_timestamped_pdf_path(job_id: str, prefix: str = "notion_export") -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_prefix = secure_filename(prefix) or "notion_export"
    filename = f"{timestamp}_{safe_prefix}_{job_id}.pdf"
    path = OUTPUT_PDF_FOLDER / filename
    return filename, str(path)

def make_uploaded_input_path(job_id: str, original_name: str) -> tuple[str, str]:
    safe_name = secure_filename(original_name or "upload")
    ext = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem or "upload"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    month_folder = UPLOADS_FOLDER / datetime.now().strftime("%Y-%m")
    month_folder.mkdir(parents=True, exist_ok=True)
    stored_name = f"{timestamp}_{stem}_{job_id}{ext}"
    path = month_folder / stored_name
    return stored_name, str(path)

def allowed_upload_extension(filename: str) -> bool:
    ext = Path(filename or "").suffix.lower().lstrip(".")
    return ext in ALLOWED_UPLOAD_EXTENSIONS

def get_client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""

def extract_pdf_text_to_file(pdf_path: str) -> str | None:
    from pypdf import PdfReader

    try:
        text = "\n".join((page.extract_text() or "") for page in PdfReader(pdf_path).pages)
        txt_path = str(OUTPUT_TXT_FOLDER / f"{Path(pdf_path).stem}.txt")
        Path(txt_path).write_text(text, encoding="utf-8")
        return txt_path
    except Exception as exc:
        print(f"PDF_TEXT_EXPORT_ERROR={exc}")
        return None

def safe_record_conversion(**values) -> int | None:
    try:
        return record_conversion(**values)
    except Exception as exc:
        print(f"DB_RECORD_ERROR={exc}")
        return None

def is_authorized_admin_request() -> bool:
    # Authentication can be added here without changing admin/download routes.
    return True

def file_path_is_allowed(path_value: str | None) -> bool:
    if not path_value:
        return False
    try:
        resolved = Path(path_value).resolve()
        allowed_roots = [UPLOADS_FOLDER.resolve(), OUTPUT_FOLDER.resolve()]
        return any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots)
    except Exception:
        return False

# ─── PDF conversion core ─────────────────────────────────────
def get_page_height_metrics(page) -> dict:
    """Measure document, body, wrapper, and element-bottom heights."""
    metrics = page.evaluate("""() => {
        const doc = document.documentElement;
        const body = document.body;
        const selectors = [
            '.notion-page-content',
            '.notion-page-content-inner',
            '.notion-frame',
            '.notion-scroller',
            'main',
            '[role="main"]',
            '#root',
            '#__next'
        ];
        const elementHeight = (el) => {
            const rect = el.getBoundingClientRect();
            const top = rect.top + window.scrollY;
            return Math.ceil(Math.max(
                el.scrollHeight || 0,
                el.offsetHeight || 0,
                el.clientHeight || 0,
                rect.height || 0,
                rect.bottom + window.scrollY,
                top + (el.scrollHeight || 0),
                top + (el.offsetHeight || 0)
            ));
        };
        const wrapperHeights = selectors.flatMap((selector) =>
            Array.from(document.querySelectorAll(selector)).map((el) => {
                return elementHeight(el);
            })
        );
        const elementBottoms = Array.from(document.body.querySelectorAll('*')).map((el) => {
            return elementHeight(el);
        });
        const domScrollHeight = Math.ceil(Math.max(
            doc.scrollHeight || 0,
            doc.offsetHeight || 0,
            doc.clientHeight || 0
        ));
        const bodyScrollHeight = Math.ceil(Math.max(
            body.scrollHeight || 0,
            body.offsetHeight || 0,
            body.clientHeight || 0
        ));
        const contentWrapperScrollHeight = Math.max(0, ...wrapperHeights);
        const maxElementBottom = Math.max(0, ...elementBottoms);
        return {
            dom_scroll_height: domScrollHeight,
            body_scroll_height: bodyScrollHeight,
            content_wrapper_scroll_height: contentWrapperScrollHeight,
            max_element_bottom: maxElementBottom,
            max_height: Math.ceil(Math.max(
                domScrollHeight,
                bodyScrollHeight,
                contentWrapperScrollHeight,
                maxElementBottom
            ))
        };
    }""")
    metrics = {key: int(value or 0) for key, value in metrics.items()}
    metrics["max_height"] = max(metrics["max_height"], 1)
    return metrics

def get_content_box_metrics(page) -> dict:
    """Measure the visible content bounding box, preferring Notion content wrappers."""
    metrics = page.evaluate("""() => {
        const selectors = [
            '.notion-page-content',
            '.notion-page-content-inner',
            'main',
            '[role="main"]',
            'article'
        ];
        const usableRect = (el) => {
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) {
                return null;
            }
            const rect = el.getBoundingClientRect();
            if (rect.width <= 0 || rect.height <= 0) {
                return null;
            }
            const top = rect.top + window.scrollY;
            const bottom = Math.max(
                rect.bottom + window.scrollY,
                top + (el.scrollHeight || 0),
                top + (el.offsetHeight || 0),
                top + (el.clientHeight || 0)
            );
            const right = Math.max(
                rect.right + window.scrollX,
                rect.left + window.scrollX + (el.scrollWidth || 0),
                rect.left + window.scrollX + (el.offsetWidth || 0),
                rect.left + window.scrollX + (el.clientWidth || 0)
            );
            return {
                left: rect.left + window.scrollX,
                top,
                right,
                bottom
            };
        };
        const wrapperRects = selectors.flatMap((selector) =>
            Array.from(document.querySelectorAll(selector)).map(usableRect).filter(Boolean)
        );
        const contentRects = Array.from(document.body.querySelectorAll('*')).flatMap((el) => {
            const tag = el.tagName.toLowerCase();
            if (['script', 'style', 'meta', 'link', 'noscript'].includes(tag)) {
                return [];
            }
            const text = (el.innerText || el.textContent || '').trim();
            const hasContent = text || ['img', 'svg', 'canvas', 'video', 'table', 'iframe'].includes(tag);
            if (!hasContent) {
                return [];
            }
            const rect = usableRect(el);
            return rect ? [rect] : [];
        });
        const rects = wrapperRects.length ? wrapperRects : contentRects;
        if (!rects.length) {
            return {left: 0, top: 0, right: document.documentElement.clientWidth, bottom: 1, width: document.documentElement.clientWidth, height: 1};
        }
        const left = Math.floor(Math.min(...rects.map((rect) => rect.left)));
        const top = Math.floor(Math.min(...rects.map((rect) => rect.top)));
        const right = Math.ceil(Math.max(...rects.map((rect) => rect.right)));
        const bottom = Math.ceil(Math.max(...rects.map((rect) => rect.bottom)));
        return {
            left,
            top,
            right,
            bottom,
            width: Math.max(1, right - left),
            height: Math.max(1, bottom - top)
        };
    }""")
    return {key: int(round(value or 0)) for key, value in metrics.items()}

def get_dom_text_layer_items(page) -> list[dict]:
    """Collect visible DOM text with CSS-pixel coordinates before screenshot cropping."""
    items = page.evaluate("""() => {
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        const results = [];
        const ignoredTags = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'INPUT', 'SELECT']);
        const normalize = (text, preserve) => {
            if (!text) return '';
            return preserve ? text.replace(/\\u00a0/g, ' ') : text.replace(/\\s+/g, ' ').trim();
        };
        while (walker.nextNode()) {
            const node = walker.currentNode;
            const parent = node.parentElement;
            if (!parent || ignoredTags.has(parent.tagName)) continue;
            if (parent.closest('[data-notion-pdf-hidden="1"]')) continue;
            const style = window.getComputedStyle(parent);
            if (
                style.display === 'none' ||
                style.visibility === 'hidden' ||
                Number(style.opacity) === 0 ||
                Number.parseFloat(style.fontSize || '0') <= 0
            ) {
                continue;
            }
            const preserve = !!parent.closest('pre, code');
            const text = normalize(node.textContent, preserve);
            if (!text.trim()) continue;
            const range = document.createRange();
            range.selectNodeContents(node);
            const rects = Array.from(range.getClientRects())
                .map((rect) => ({
                    left: rect.left + window.scrollX,
                    top: rect.top + window.scrollY,
                    width: rect.width,
                    height: rect.height,
                    right: rect.right + window.scrollX,
                    bottom: rect.bottom + window.scrollY,
                }))
                .filter((rect) => rect.width > 0 && rect.height > 0);
            range.detach();
            if (!rects.length) continue;
            const docHeight = Math.max(document.documentElement.scrollHeight || 0, document.body.scrollHeight || 0);
            const visibleRects = rects.filter((rect) => rect.bottom >= 0 && rect.top <= docHeight);
            if (!visibleRects.length) continue;
            const first = visibleRects[0];
            const left = Math.min(...visibleRects.map((rect) => rect.left));
            const top = Math.min(...visibleRects.map((rect) => rect.top));
            const right = Math.max(...visibleRects.map((rect) => rect.right));
            const bottom = Math.max(...visibleRects.map((rect) => rect.bottom));
            results.push({
                text,
                left: first.left,
                top: first.top,
                width: Math.max(first.width, right - left),
                height: first.height,
                box_left: left,
                box_top: top,
                box_width: right - left,
                box_height: bottom - top,
                font_size: Number.parseFloat(style.fontSize || '12') || 12,
                font_weight: style.fontWeight || '',
                line_height: style.lineHeight || '',
                tag: parent.tagName.toLowerCase(),
                preserve_space: preserve,
            });
        }
        return results;
    }""")
    return items or []

def hide_notion_public_banner(page) -> dict:
    """Hide Notion public sign-up/login chrome without touching document content."""
    result = page.evaluate("""() => {
        const phrases = [
            "You're almost there",
            "sign up to start building in Notion today",
            "Sign up or login",
        ];
        const normalize = (text) => (text || '').replace(/\\s+/g, ' ').trim();
        const matchingPhrases = (el) => {
            const text = normalize(el.innerText || el.textContent || '');
            return phrases.filter((phrase) => text.includes(phrase));
        };
        const hasDocumentSignals = (el) => {
            if (!el) return false;
            const selector = [
                'main',
                'article',
                '.notion-page-content',
                '.notion-page-content-inner',
                '[data-block-id]',
                '[contenteditable="true"]',
                'h1',
                'h2',
                'h3'
            ].join(',');
            return !!el.matches(selector) || !!el.querySelector(selector);
        };
        const getBox = (el) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return {
                tag: el.tagName.toLowerCase(),
                role: el.getAttribute('role') || '',
                text: normalize(el.innerText || el.textContent || '').slice(0, 180),
                phrases: matchingPhrases(el),
                top: Math.round(rect.top + window.scrollY),
                left: Math.round(rect.left + window.scrollX),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                position: style.position,
                className: String(el.className || '').slice(0, 160),
            };
        };
        const phraseNodes = Array.from(document.querySelectorAll('body *'))
            .filter((el) => matchingPhrases(el).length > 0);
        const candidateSet = new Set();
        for (const el of phraseNodes) {
            const chrome = el.closest('[role="banner"], header, nav');
            candidateSet.add(chrome || el);
        }
        const candidates = Array.from(candidateSet);
        const detected = candidates.map(getBox);
        const removed = [];
        for (const el of candidates) {
            if (!el || el.dataset.notionPdfHidden === '1') continue;
            if (!matchingPhrases(el).length) continue;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const isTopChrome = (
                (el.getAttribute('role') || '').toLowerCase() === 'banner' ||
                ['header', 'nav'].includes(el.tagName.toLowerCase()) ||
                ['fixed', 'sticky'].includes(style.position)
            );
            if (!isTopChrome) continue;
            if (hasDocumentSignals(el)) continue;
            if (rect.top > 320 && !['fixed', 'sticky'].includes(style.position)) continue;
            if (rect.height > Math.max(220, window.innerHeight * 0.35)) continue;
            const beforeBox = getBox(el);
            el.dataset.notionPdfHidden = '1';
            el.style.setProperty('display', 'none', 'important');
            el.style.setProperty('visibility', 'hidden', 'important');
            removed.push(beforeBox);
        }
        const remainingText = normalize(document.body ? document.body.innerText : '');
        return {
            detected_count: detected.length,
            detected,
            removed_count: removed.length,
            removed,
            remaining_banner_text: phrases.filter((phrase) => remainingText.includes(phrase)),
        };
    }""")
    return result or {"detected_count": 0, "detected": [], "removed_count": 0, "removed": [], "remaining_banner_text": []}

def capture_debug_viewport(page, name: str) -> str | None:
    try:
        DEBUG_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        path = DEBUG_OUTPUT_FOLDER / name
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(100)
        page.screenshot(path=str(path), type="png", timeout=60000)
        return str(path)
    except Exception as exc:
        print(f"DEBUG_SCREENSHOT_ERROR={name}:{exc}")
        return None

def get_first_visible_content_info(page) -> dict:
    info = page.evaluate("""() => {
        const normalize = (text) => (text || '').replace(/\\s+/g, ' ').trim();
        const isVisibleElement = (el) => {
            if (!el || !el.isConnected) return false;
            if (el.closest('[data-notion-pdf-hidden="1"], script, style, noscript')) return false;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || Number.parseFloat(style.opacity || '1') === 0) {
                return false;
            }
            return true;
        };
        const textItems = [];
        const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT, {
            acceptNode(node) {
                const text = normalize(node.textContent || '');
                if (!text) return NodeFilter.FILTER_REJECT;
                const parent = node.parentElement;
                if (!isVisibleElement(parent)) return NodeFilter.FILTER_REJECT;
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        while (walker.nextNode()) {
            const node = walker.currentNode;
            const range = document.createRange();
            range.selectNodeContents(node);
            const rects = Array.from(range.getClientRects())
                .filter((rect) => rect.width > 0 && rect.height > 0)
                .map((rect) => ({
                    text: normalize(node.textContent || ''),
                    top: rect.top + window.scrollY,
                    left: rect.left + window.scrollX,
                    width: rect.width,
                    height: rect.height,
                }));
            range.detach();
            textItems.push(...rects);
        }
        const mediaItems = Array.from(document.querySelectorAll('img, video, canvas, svg'))
            .filter(isVisibleElement)
            .map((el) => {
                const rect = el.getBoundingClientRect();
                return {
                    text: el.getAttribute('alt') || el.getAttribute('aria-label') || el.tagName.toLowerCase(),
                    top: rect.top + window.scrollY,
                    left: rect.left + window.scrollX,
                    width: rect.width,
                    height: rect.height,
                };
            })
            .filter((item) => item.width > 0 && item.height > 0);
        const items = textItems.concat(mediaItems)
            .filter((item) => item.top >= 0)
            .sort((a, b) => (a.top - b.top) || (a.left - b.left));
        const first = items[0] || null;
        return {
            content_top: first ? Math.round(first.top) : 0,
            crop_top: 0,
            first_visible_text: first ? String(first.text || '').slice(0, 160) : '',
            first_visible_text_y: first ? Math.round(first.top) : null,
            first_visible_item_count: items.length,
        };
    }""")
    return info or {
        "content_top": 0,
        "crop_top": 0,
        "first_visible_text": "",
        "first_visible_text_y": None,
        "first_visible_item_count": 0,
    }

def expand_notion_toggles(page, max_passes: int = 8) -> dict:
    """Expand closed Notion-like toggle blocks before screenshot capture."""
    total_clicked = 0
    total_details_opened = 0
    pass_logs = []
    for pass_index in range(max_passes):
        result = page.evaluate("""() => {
            const normalize = (text) => (text || '').replace(/\\s+/g, ' ').trim();
            const isDocumentRouteLink = (el) => {
                const href = el.getAttribute && el.getAttribute('href');
                return !!href;
            };
            const isToggleCandidate = (el) => {
                if (!el || el.dataset.notionPdfToggleExpanded === '1') return false;
                if (isDocumentRouteLink(el)) return false;
                const ariaExpanded = (el.getAttribute('aria-expanded') || '').toLowerCase();
                if (ariaExpanded !== 'false') return false;
                const role = (el.getAttribute('role') || '').toLowerCase();
                const tag = el.tagName.toLowerCase();
                if (role !== 'button' && tag !== 'button' && tag !== 'summary') return false;
                const text = normalize(el.innerText || el.textContent || '');
                const classText = [
                    el.className || '',
                    el.parentElement ? el.parentElement.className || '' : '',
                    el.closest('[class]') ? el.closest('[class]').className || '' : '',
                ].join(' ').toLowerCase();
                const hasNotionContext = !!el.closest('.notion-toggle, .notion-toggle-block, [data-block-id], [data-content-editable-leaf]');
                const hasToggleClass = /toggle|collapse|expand|disclosure/.test(classText);
                const hasControlledRegion = !!el.getAttribute('aria-controls');
                const hasArrowText = /^[▶▸▾▼]/.test(text);
                const hasSmallRect = (() => {
                    const rect = el.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && rect.width <= 800 && rect.height <= 80;
                })();
                return hasSmallRect && (hasNotionContext || hasToggleClass || hasControlledRegion || hasArrowText);
            };

            const details = Array.from(document.querySelectorAll('details:not([open])'));
            let detailsOpened = 0;
            for (const item of details) {
                if (item.closest('[data-notion-pdf-hidden="1"]')) continue;
                item.open = true;
                detailsOpened += 1;
            }

            const candidates = Array.from(document.querySelectorAll('[aria-expanded="false"], button, [role="button"]'))
                .filter(isToggleCandidate)
                .slice(0, 80);
            let clicked = 0;
            const clickedItems = [];
            for (const el of candidates) {
                const beforeUrl = location.href;
                try {
                    el.dataset.notionPdfToggleExpanded = '1';
                    el.scrollIntoView({block: 'center', inline: 'nearest'});
                    el.click();
                    clicked += 1;
                    clickedItems.push({
                        tag: el.tagName.toLowerCase(),
                        text: normalize(el.innerText || el.textContent || '').slice(0, 80),
                        className: String(el.className || '').slice(0, 120),
                    });
                    if (location.href !== beforeUrl && history.length > 1) {
                        history.back();
                    }
                } catch (err) {
                    clickedItems.push({error: String(err).slice(0, 120)});
                }
            }
            return {
                clicked,
                details_opened: detailsOpened,
                clicked_items: clickedItems,
                height: Math.max(document.documentElement.scrollHeight || 0, document.body ? document.body.scrollHeight || 0 : 0),
            };
        }""")
        result = result or {"clicked": 0, "details_opened": 0, "clicked_items": [], "height": 0}
        pass_logs.append({"pass": pass_index + 1, **result})
        total_clicked += int(result.get("clicked") or 0)
        total_details_opened += int(result.get("details_opened") or 0)
        if not result.get("clicked") and not result.get("details_opened"):
            break
        page.wait_for_timeout(350)
    return {
        "passes": len(pass_logs),
        "clicked": total_clicked,
        "details_opened": total_details_opened,
        "logs": pass_logs,
    }

def preprocess_page_before_capture(
    page,
    expand_toggles: bool = True,
    remove_banners: bool = True,
    debug_stem: str | None = None,
) -> dict:
    result = {
        "banner_cleanup": None,
        "toggle_expansion": None,
        "debug_before_screenshot": None,
        "debug_after_screenshot": None,
        "errors": [],
    }
    safe_stem = secure_filename(debug_stem or "preprocess") or "preprocess"
    result["debug_before_screenshot"] = capture_debug_viewport(page, f"{safe_stem}_preprocess_before.png")
    if remove_banners:
        try:
            before = get_page_height_metrics(page)
            banner_cleanup = hide_notion_public_banner(page)
            after = get_page_height_metrics(page)
            result["banner_cleanup"] = {**banner_cleanup, "before_height": before["max_height"], "after_height": after["max_height"]}
            if banner_cleanup.get("removed_count") or banner_cleanup.get("remaining_banner_text"):
                print(
                    "NOTION_BANNER_CLEANUP="
                    f"detected:{banner_cleanup.get('detected_count')},"
                    f"removed:{banner_cleanup.get('removed_count')},"
                    f"remaining:{banner_cleanup.get('remaining_banner_text')},"
                    f"height:{before['max_height']}->{after['max_height']}"
                )
                print(f"NOTION_BANNER_BOXES={banner_cleanup.get('removed') or banner_cleanup.get('detected')}")
        except Exception as exc:
            result["errors"].append(f"banner cleanup failed: {exc}")
            print(f"NOTION_BANNER_CLEANUP_ERROR={exc}")
    if expand_toggles:
        try:
            before = get_page_height_metrics(page)
            toggle_expansion = expand_notion_toggles(page)
            page.wait_for_timeout(500)
            after = get_page_height_metrics(page)
            result["toggle_expansion"] = {**toggle_expansion, "before_height": before["max_height"], "after_height": after["max_height"]}
            if toggle_expansion.get("clicked") or toggle_expansion.get("details_opened"):
                print(
                    "NOTION_TOGGLE_EXPANSION="
                    f"clicked:{toggle_expansion.get('clicked')},"
                    f"details:{toggle_expansion.get('details_opened')},"
                    f"passes:{toggle_expansion.get('passes')},"
                    f"height:{before['max_height']}->{after['max_height']}"
                )
        except Exception as exc:
            result["errors"].append(f"toggle expansion failed: {exc}")
            print(f"NOTION_TOGGLE_EXPANSION_ERROR={exc}")
    result["debug_after_screenshot"] = capture_debug_viewport(page, f"{safe_stem}_preprocess_after.png")
    try:
        page.evaluate("(value) => { window.__notionPdfPreprocessResult = value; }", result)
    except Exception as exc:
        print(f"PREPROCESS_RESULT_STORE_ERROR={exc}")
    return result

def wait_for_page_render_stability(page, timeout_ms: int = PDF_RENDER_STABLE_TIMEOUT_MS) -> dict:
    """Wait for fonts, lazy images, and document height to settle."""
    start = time.time()
    image_stats = {"total": 0, "loaded": 0, "incomplete": 0}
    try:
        page.evaluate("""async () => {
            if (document.fonts && document.fonts.ready) {
                await document.fonts.ready;
            }
        }""")
    except Exception as exc:
        print(f"FONT_READY_WAIT_ERROR={exc}")

    last_height = 0
    stable_count = 0
    scroll_step = 1200
    while (time.time() - start) * 1000 < timeout_ms:
        try:
            metrics = get_page_height_metrics(page)
            height = max(metrics["max_height"], 1080)
            for y in range(0, height + scroll_step, scroll_step):
                page.evaluate("(y) => window.scrollTo(0, y)", y)
                page.wait_for_timeout(80)
            page.evaluate("() => window.scrollTo(0, 0)")
            page.wait_for_timeout(250)
            image_stats = page.evaluate("""() => {
                const images = Array.from(document.images || []);
                return {
                    total: images.length,
                    loaded: images.filter((img) => img.complete && img.naturalWidth > 0).length,
                    incomplete: images.filter((img) => !img.complete || img.naturalWidth <= 0).length,
                };
            }""")
            metrics = get_page_height_metrics(page)
            current_height = metrics["max_height"]
            if abs(current_height - last_height) <= 2 and int(image_stats.get("incomplete") or 0) == 0:
                stable_count += 1
            else:
                stable_count = 0
            last_height = current_height
            if stable_count >= 2:
                break
        except Exception as exc:
            print(f"RENDER_STABILITY_WAIT_ERROR={exc}")
            break
    elapsed_ms = int((time.time() - start) * 1000)
    print(
        "RENDER_STABILITY="
        f"elapsed_ms:{elapsed_ms},"
        f"height:{last_height},"
        f"images:{image_stats.get('loaded', 0)}/{image_stats.get('total', 0)},"
        f"incomplete:{image_stats.get('incomplete', 0)}"
    )
    return {"elapsed_ms": elapsed_ms, "height": last_height, **image_stats}

def apply_capture_safety_styles(page) -> dict:
    """Relax clipping around table/database media before measuring and screenshotting."""
    result = page.evaluate("""() => {
        const styleId = 'notion-pdf-capture-safety-style';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
              .notion-collection-view,
              .notion-table-view,
              .notion-list-view,
              .notion-gallery-view,
              .notion-board-view,
              [class*="collection"],
              [class*="table"],
              [class*="database"],
              [role="table"],
              table,
              tbody,
              tr,
              td,
              th {
                overflow: visible !important;
                max-height: none !important;
                clip-path: none !important;
                contain: none !important;
              }
              img, video, canvas, iframe {
                max-height: none !important;
                clip-path: none !important;
              }
              [data-notion-pdf-hidden="1"] {
                display: none !important;
                visibility: hidden !important;
              }
            `;
            document.head.appendChild(style);
        }
        let adjusted = 0;
        const candidates = Array.from(document.querySelectorAll([
            '.notion-collection-view',
            '.notion-table-view',
            '[class*="collection"]',
            '[class*="table"]',
            '[class*="database"]',
            '[role="table"]',
            'table',
            'td',
            'th'
        ].join(',')));
        for (const el of candidates) {
            const style = window.getComputedStyle(el);
            if (style.overflow !== 'visible' || style.overflowY !== 'visible' || style.maxHeight !== 'none') {
                el.dataset.notionPdfOverflowAdjusted = '1';
                el.style.setProperty('overflow', 'visible', 'important');
                el.style.setProperty('overflow-y', 'visible', 'important');
                el.style.setProperty('overflow-x', 'visible', 'important');
                el.style.setProperty('max-height', 'none', 'important');
                el.style.setProperty('clip-path', 'none', 'important');
                el.style.setProperty('contain', 'none', 'important');
                adjusted += 1;
            }
        }
        return {adjusted};
    }""")
    return result or {"adjusted": 0}

def log_potential_clipping_blocks(page, output_path: str) -> list[dict]:
    logs = page.evaluate("""() => {
        const rows = [];
        const candidates = Array.from(document.querySelectorAll([
            '.notion-collection-view',
            '.notion-table-view',
            '[class*="collection"]',
            '[class*="table"]',
            '[class*="database"]',
            '[role="table"]',
            'table',
            'td',
            'th',
            'img'
        ].join(',')));
        for (const el of candidates) {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const clipped = (
                el.scrollHeight > el.clientHeight + 2 ||
                el.scrollWidth > el.clientWidth + 2 ||
                ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflow) ||
                ['hidden', 'clip', 'auto', 'scroll'].includes(style.overflowY)
            );
            if (!clipped && el.tagName.toLowerCase() !== 'img') continue;
            rows.push({
                tag: el.tagName.toLowerCase(),
                className: String(el.className || '').slice(0, 160),
                top: Math.round(rect.top + window.scrollY),
                bottom: Math.round(rect.bottom + window.scrollY),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                clientHeight: el.clientHeight || 0,
                scrollHeight: el.scrollHeight || 0,
                overflow: style.overflow,
                overflowY: style.overflowY,
                src: el.tagName.toLowerCase() === 'img' ? (el.currentSrc || el.src || '').slice(0, 160) : '',
            });
            if (rows.length >= 200) break;
        }
        return rows;
    }""")
    try:
        import json
        Path(output_path).write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        print(f"CLIPPING_DEBUG_WRITE_ERROR={exc}")
    print(f"CLIPPING_DEBUG_BLOCKS={len(logs or [])},path={output_path}")
    return logs or []

def capture_page_to_png_chunks(page, png_path: str, width: int, height: int, chunk_height: int, scale: int) -> dict:
    from PIL import Image

    chunk_height = max(1000, int(chunk_height))
    chunk_dir = DEBUG_OUTPUT_FOLDER / f"chunks_{Path(png_path).stem}"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunk_files = []
    failures = []
    page.evaluate("() => window.scrollTo(0, 0)")
    page.wait_for_timeout(150)
    for index, y in enumerate(range(0, height, chunk_height)):
        current_height = min(chunk_height, height - y)
        chunk_path = chunk_dir / f"chunk_{index:04d}_{y}.png"
        for attempt in range(1, PDF_SCREENSHOT_CHUNK_RETRIES + 1):
            try:
                page.set_viewport_size({"width": width, "height": max(1, current_height)})
                page.evaluate("(y) => window.scrollTo(0, y)", y)
                page.wait_for_timeout(180)
                page.screenshot(
                    path=str(chunk_path),
                    type="png",
                    timeout=max(60000, PDF_RENDER_STABLE_TIMEOUT_MS),
                )
                chunk_files.append(chunk_path)
                print(f"SCREENSHOT_CHUNK index={index} y={y} height={current_height} path={chunk_path}")
                break
            except Exception as exc:
                failures.append({"index": index, "y": y, "height": current_height, "attempt": attempt, "error": str(exc)})
                print(f"SCREENSHOT_CHUNK_ERROR index={index} y={y} attempt={attempt} error={exc}")
                page.wait_for_timeout(500 * attempt)
        else:
            raise RuntimeError(f"Chunk screenshot failed at index={index}, y={y}, height={current_height}: {failures[-1]['error']}")

    if not chunk_files:
        raise RuntimeError("No screenshot chunks were captured")

    opened = [Image.open(path).convert("RGB") for path in chunk_files]
    try:
        final_width = max(image.width for image in opened)
        final_height = sum(image.height for image in opened)
        stitched = Image.new("RGB", (final_width, final_height), PDF_BACKGROUND_COLOR)
        paste_y = 0
        for image in opened:
            stitched.paste(image, (0, paste_y))
            paste_y += image.height
        stitched.save(png_path)
    finally:
        for image in opened:
            image.close()

    print(
        "SCREENSHOT_STITCH="
        f"chunks:{len(chunk_files)},"
        f"css_height:{height},"
        f"png_path:{png_path},"
        f"chunk_height:{chunk_height},"
        f"scale:{scale}"
    )
    return {
        "screenshot_chunk_count": len(chunk_files),
        "screenshot_chunk_height": chunk_height,
        "screenshot_chunk_failures": failures,
        "screenshot_chunk_dir": str(chunk_dir),
    }

def assert_single_page_pdf(pdf_path: str) -> int:
    from pypdf import PdfReader

    page_count = len(PdfReader(pdf_path).pages)
    if page_count != 1:
        raise RuntimeError(
            f"PDF가 1페이지가 아닙니다. 실제 페이지 수: {page_count}. 파일: {pdf_path}. "
            "문서 높이가 Chromium 또는 PDF 뷰어의 단일 페이지 한계를 초과했을 수 있습니다."
        )
    return page_count

def get_pdf_page_info(pdf_path: str) -> dict:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    page = reader.pages[0]
    return {
        "pages": len(reader.pages),
        "pdf_page_width": float(page.mediabox.width),
        "pdf_page_height": float(page.mediabox.height),
    }

def get_png_size(png_path: str) -> tuple[int, int]:
    with open(png_path, "rb") as fp:
        header = fp.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"Invalid PNG screenshot: {png_path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    return width, height

def extract_pdf_text_length(pdf_path: str) -> int:
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return len(text.strip())

def preprocess_ocr_chunk(image, mode: str):
    from PIL import ImageEnhance, ImageFilter

    gray = image.convert("L")
    if mode == "sharp":
        return ImageEnhance.Contrast(gray).enhance(1.45).filter(ImageFilter.SHARPEN)
    if mode == "contrast":
        return ImageEnhance.Contrast(gray).enhance(1.85).filter(ImageFilter.SHARPEN)
    if mode == "threshold":
        enhanced = ImageEnhance.Contrast(gray).enhance(1.65).filter(ImageFilter.SHARPEN)
        return enhanced.point(lambda px: 255 if px > 185 else 0, mode="1").convert("L")
    return gray

def run_tesseract_tsv(image_path: str, language: str, psm: int = 6) -> list[dict]:
    import csv
    import subprocess

    command = [
        "tesseract",
        image_path,
        "stdout",
        "-l",
        language,
        "--psm",
        str(psm),
        "tsv",
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=PDF_OCR_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "").strip())

    rows = []
    reader = csv.DictReader(completed.stdout.splitlines(), delimiter="\t")
    for row in reader:
        text = (row.get("text") or "").strip()
        if not text:
            continue
        try:
            conf = float(row.get("conf") or -1)
            left = int(float(row.get("left") or 0))
            top = int(float(row.get("top") or 0))
            width = int(float(row.get("width") or 0))
            height = int(float(row.get("height") or 0))
        except ValueError:
            continue
        if conf < 0 or width <= 0 or height <= 0:
            continue
        rows.append({
            "text": text,
            "conf": conf,
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        })
    return rows

def ocr_image_chunks(png_path: str, language: str = PDF_OCR_LANGUAGE) -> dict:
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    tesseract_bin = shutil.which("tesseract")
    if not tesseract_bin:
        return {
            "words": [],
            "chunks": [],
            "failed_chunks": [],
            "text_length": 0,
            "status": "skipped",
            "error": "tesseract command not found",
        }

    variants = ["sharp", "contrast", "threshold"]
    all_words = []
    chunks = []
    failed_chunks = []

    with Image.open(png_path) as source_image:
        source = source_image.convert("RGB")
        image_width, image_height = source.size
        chunk_height = min(max(PDF_OCR_CHUNK_HEIGHT_PX, 1200), image_height)
        overlap = min(PDF_OCR_CHUNK_OVERLAP_PX, max(0, chunk_height // 10))
        y_positions = []
        y = 0
        while y < image_height:
            y_positions.append(y)
            if y + chunk_height >= image_height:
                break
            y += max(1, chunk_height - overlap)

        with tempfile.TemporaryDirectory(prefix="notion_pdf_ocr_") as temp_dir:
            temp_dir_path = Path(temp_dir)
            for chunk_index, chunk_top in enumerate(y_positions):
                chunk_bottom = min(image_height, chunk_top + chunk_height)
                chunk = source.crop((0, chunk_top, image_width, chunk_bottom))
                best_rows = []
                best_variant = None
                best_error = None

                for variant in variants:
                    processed = preprocess_ocr_chunk(chunk, variant)
                    chunk_path = temp_dir_path / f"chunk_{chunk_index:04d}_{variant}.png"
                    processed.save(chunk_path)
                    try:
                        rows = run_tesseract_tsv(str(chunk_path), language=language, psm=6)
                    except Exception as exc:
                        best_error = str(exc)
                        rows = []
                    if sum(len(row["text"]) for row in rows) > sum(len(row["text"]) for row in best_rows):
                        best_rows = rows
                        best_variant = variant
                    min_chars = max(8, int((chunk_bottom - chunk_top) * image_width * PDF_OCR_MIN_TEXT_RATIO / 100))
                    if sum(len(row["text"]) for row in best_rows) >= min_chars and variant != "threshold":
                        break

                chunk_text_length = sum(len(row["text"]) for row in best_rows)
                chunk_info = {
                    "index": chunk_index,
                    "top": chunk_top,
                    "bottom": chunk_bottom,
                    "height": chunk_bottom - chunk_top,
                    "variant": best_variant,
                    "word_count": len(best_rows),
                    "text_length": chunk_text_length,
                    "status": "ok" if chunk_text_length > 0 else "failed",
                }
                chunks.append(chunk_info)
                if chunk_text_length == 0:
                    failed_chunks.append({
                        "index": chunk_index,
                        "top": chunk_top,
                        "bottom": chunk_bottom,
                        "error": best_error or "no OCR text detected",
                    })
                    continue

                for row in best_rows:
                    row = dict(row)
                    if chunk_index > 0 and row["top"] < overlap:
                        continue
                    row["chunk_index"] = chunk_index
                    row["page_left"] = row["left"]
                    row["page_top"] = chunk_top + row["top"]
                    all_words.append(row)

    return {
        "words": all_words,
        "chunks": chunks,
        "failed_chunks": failed_chunks,
        "text_length": sum(len(word["text"]) for word in all_words),
        "status": "ok" if all_words else "failed",
        "error": None if all_words else "no OCR text detected",
    }

def build_tounicode_cmap(texts: list[str]) -> bytes:
    chars = sorted({char for text in texts for char in text if 0 < ord(char) <= 0xFFFF}, key=ord)
    lines = [
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
        "/CMapName /NotionOCRUnicode def",
        "/CMapType 2 def",
        "1 begincodespacerange",
        "<0000> <FFFF>",
        "endcodespacerange",
    ]
    for start in range(0, len(chars), 100):
        group = chars[start:start + 100]
        lines.append(f"{len(group)} beginbfchar")
        for char in group:
            code = f"{ord(char):04X}"
            lines.append(f"<{code}> <{code}>")
        lines.append("endbfchar")
    lines.extend(["endcmap", "CMapName currentdict /CMap defineresource pop", "end", "end"])
    return ("\n".join(lines) + "\n").encode("ascii")

def text_to_pdf_hex(text: str) -> str:
    return "".join(f"{ord(char):04X}" for char in text if 0 < ord(char) <= 0xFFFF)

def add_invisible_text_layer_to_pdf(
    pdf_path: str,
    words: list[dict],
    image_width: int,
    image_height: int,
) -> int:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import ArrayObject, DecodedStreamObject, DictionaryObject, NameObject, NumberObject, TextStringObject

    if not words:
        return 0

    reader = PdfReader(pdf_path)
    writer = PdfWriter()
    page = reader.pages[0]
    pdf_width = float(page.mediabox.width)
    pdf_height = float(page.mediabox.height)
    scale_x = pdf_width / max(image_width, 1)
    scale_y = pdf_height / max(image_height, 1)

    writer.add_page(page)
    page = writer.pages[0]

    tounicode = DecodedStreamObject()
    tounicode.set_data(build_tounicode_cmap([word["text"] for word in words]))
    tounicode_ref = writer._add_object(tounicode)

    cid_font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/CIDFontType0"),
        NameObject("/BaseFont"): NameObject("/HYGoThic-Medium"),
        NameObject("/CIDSystemInfo"): DictionaryObject({
            NameObject("/Registry"): TextStringObject("Adobe"),
            NameObject("/Ordering"): TextStringObject("Korea1"),
            NameObject("/Supplement"): NumberObject(2),
        }),
    })
    cid_font_ref = writer._add_object(cid_font)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type0"),
        NameObject("/BaseFont"): NameObject("/HYGoThic-Medium"),
        NameObject("/Encoding"): NameObject("/Identity-H"),
        NameObject("/DescendantFonts"): ArrayObject([cid_font_ref]),
        NameObject("/ToUnicode"): tounicode_ref,
    })
    font_ref = writer._add_object(font)

    resources = page.get("/Resources")
    if resources is None:
        resources = DictionaryObject()
        page[NameObject("/Resources")] = resources
    else:
        resources = resources.get_object()
    fonts = resources.get("/Font")
    if fonts is None:
        fonts = DictionaryObject()
        resources[NameObject("/Font")] = fonts
    else:
        fonts = fonts.get_object()
    fonts[NameObject("/Focr")] = font_ref

    commands = ["q", "BT", "3 Tr"]
    inserted = 0
    for word in words:
        text_hex = text_to_pdf_hex(word["text"])
        if not text_hex:
            continue
        x = max(0, word["page_left"] * scale_x)
        y = max(0, pdf_height - ((word["page_top"] + word["height"]) * scale_y))
        font_size = max(3.0, word["height"] * scale_y * 0.9)
        commands.append(f"/Focr {font_size:.3f} Tf")
        commands.append(f"1 0 0 1 {x:.3f} {y:.3f} Tm <{text_hex}> Tj")
        inserted += 1
    commands.extend(["ET", "Q"])

    stream = DecodedStreamObject()
    stream.set_data(("\n".join(commands) + "\n").encode("ascii"))
    stream_ref = writer._add_object(stream)
    existing_contents = page.get("/Contents")
    if existing_contents is None:
        page[NameObject("/Contents")] = stream_ref
    elif isinstance(existing_contents, ArrayObject):
        existing_contents.append(stream_ref)
    else:
        page[NameObject("/Contents")] = ArrayObject([existing_contents, stream_ref])

    temp_output = str(Path(pdf_path).with_suffix(".ocr-layer.pdf"))
    with open(temp_output, "wb") as fp:
        writer.write(fp)
    Path(temp_output).replace(pdf_path)
    return inserted

def transform_dom_items_to_final_image(dom_items: list[dict], crop_metrics: dict, image_width: int, image_height: int) -> list[dict]:
    scale = crop_metrics.get("image_coordinate_scale", 1) or 1
    crop_left = crop_metrics.get("image_crop_left_px", 0) or 0
    paste_x = crop_metrics.get("image_paste_x_px", 0) or 0
    rebalance_shift = crop_metrics.get("image_rebalance_shift_x_px", 0) or 0
    transformed = []
    for item in dom_items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        page_left = (float(item.get("left") or 0) * scale) - crop_left + paste_x + rebalance_shift
        page_top = float(item.get("top") or 0) * scale
        width = max(1, float(item.get("width") or 1) * scale)
        height = max(1, float(item.get("height") or item.get("font_size") or 12) * scale)
        if page_top > image_height or page_left + width < 0 or page_left > image_width:
            continue
        transformed.append({
            "text": text,
            "page_left": max(0, page_left),
            "page_top": max(0, min(page_top, image_height - 1)),
            "width": min(width, image_width),
            "height": height,
            "font_size": item.get("font_size"),
            "font_weight": item.get("font_weight"),
            "line_height": item.get("line_height"),
            "source": "dom",
        })
    return transformed

def word_overlaps_dom(word: dict, dom_items: list[dict]) -> bool:
    center_x = word["page_left"] + (word["width"] / 2)
    center_y = word["page_top"] + (word["height"] / 2)
    for item in dom_items:
        pad_x = max(4, item["height"] * 0.6)
        pad_y = max(3, item["height"] * 0.5)
        if (
            item["page_left"] - pad_x <= center_x <= item["page_left"] + item["width"] + pad_x and
            item["page_top"] - pad_y <= center_y <= item["page_top"] + item["height"] + pad_y
        ):
            return True
    return False

def word_in_dom_text_band(word: dict, dom_items: list[dict]) -> bool:
    center_y = word["page_top"] + (word["height"] / 2)
    for item in dom_items:
        pad_y = max(4, item["height"] * 0.8)
        if item["page_top"] - pad_y <= center_y <= item["page_top"] + item["height"] + pad_y:
            return True
    return False

def empty_text_layer_info(mode: str, status: str, error: str | None = None) -> dict:
    return {
        "text_layer_mode": mode,
        "text_layer_status": status,
        "text_layer_error": error,
        "dom_text_layer_applied": False,
        "dom_text_layer_items": 0,
        "dom_text_layer_chars": 0,
        "dom_text_layer_extracted_chars": 0,
        "ocr_requested": False,
        "ocr_applied": False,
        "ocr_status": "disabled",
        "ocr_language": PDF_OCR_LANGUAGE,
        "ocr_engine": None,
        "ocr_error": None,
        "ocr_text_length": 0,
        "ocr_extracted_text_length": 0,
        "ocr_inserted_words": 0,
        "ocr_chunk_count": 0,
        "ocr_chunks": [],
        "ocr_failed_chunks": [],
    }

def apply_text_layers_to_pdf(
    pdf_path: str,
    png_path: str,
    image_width: int,
    image_height: int,
    mode: str,
    dom_items: list[dict],
    crop_metrics: dict,
    language: str = PDF_OCR_LANGUAGE,
) -> dict:
    mode = normalize_text_layer_mode(mode, mode != "none")
    if mode == "none":
        return empty_text_layer_info(mode, "disabled")

    info = empty_text_layer_info(mode, "applied")
    dom_layer_items = transform_dom_items_to_final_image(dom_items, crop_metrics, image_width, image_height)
    inserted_dom = 0
    ocr_words = []
    ocr_result = None

    if mode in ("dom", "hybrid") and dom_layer_items:
        inserted_dom = len(dom_layer_items)
        info.update({
            "dom_text_layer_applied": True,
            "dom_text_layer_items": inserted_dom,
            "dom_text_layer_chars": sum(len(item["text"]) for item in dom_layer_items),
        })

    if mode in ("ocr", "hybrid"):
        if not shutil.which("tesseract"):
            info.update({
                "ocr_requested": True,
                "ocr_status": "skipped",
                "ocr_error": "tesseract command not found",
                "text_layer_status": "partial" if inserted_dom else "skipped",
            })
        else:
            try:
                ocr_result = ocr_image_chunks(png_path, language=language)
                ocr_words = ocr_result["words"]
                if mode == "hybrid" and dom_layer_items:
                    ocr_words = [
                        word for word in ocr_words
                        if not word_overlaps_dom(word, dom_layer_items)
                        and not word_in_dom_text_band(word, dom_layer_items)
                    ]
                info.update({
                    "ocr_requested": True,
                    "ocr_applied": bool(ocr_words),
                    "ocr_status": "applied" if ocr_words else "insufficient_text",
                    "ocr_language": language,
                    "ocr_engine": "tesseract-tsv+pypdf-text-layer",
                    "ocr_error": None if ocr_words else "no non-DOM OCR words inserted",
                    "ocr_text_length": ocr_result["text_length"],
                    "ocr_inserted_words": len(ocr_words),
                    "ocr_chunk_count": len(ocr_result["chunks"]),
                    "ocr_chunks": ocr_result["chunks"],
                    "ocr_failed_chunks": ocr_result["failed_chunks"],
                })
            except Exception as exc:
                info.update({
                    "ocr_requested": True,
                    "ocr_applied": False,
                    "ocr_status": "failed",
                    "ocr_language": language,
                    "ocr_engine": "tesseract-tsv+pypdf-text-layer",
                    "ocr_error": str(exc),
                    "text_layer_status": "partial" if inserted_dom else "failed",
                })

    combined_items = []
    if mode in ("dom", "hybrid"):
        combined_items.extend(dom_layer_items)
    if mode in ("ocr", "hybrid"):
        combined_items.extend(ocr_words)
    inserted_total = add_invisible_text_layer_to_pdf(pdf_path, combined_items, image_width, image_height)
    if inserted_total == 0 and mode != "none":
        info["text_layer_status"] = "failed"
        info["text_layer_error"] = "no text layer items inserted"

    extracted_text_length = extract_pdf_text_length(pdf_path)
    info["dom_text_layer_extracted_chars"] = extracted_text_length if inserted_dom else 0
    info["ocr_extracted_text_length"] = extracted_text_length if info["ocr_requested"] else 0
    if extracted_text_length == 0:
        info["text_layer_status"] = "failed"
        info["text_layer_error"] = "no extractable text after text layer insertion"
    elif info["text_layer_status"] == "applied" and mode == "hybrid" and not inserted_dom and not info["ocr_applied"]:
        info["text_layer_status"] = "failed"
    return info

def apply_ocr_to_pdf(
    pdf_path: str,
    png_path: str,
    image_width: int,
    image_height: int,
    enabled: bool = True,
    language: str = PDF_OCR_LANGUAGE,
) -> dict:
    """Apply chunked OCR to the final image and add an invisible PDF text layer."""
    if not enabled:
        return {
            "ocr_requested": False,
            "ocr_applied": False,
            "ocr_status": "disabled",
            "ocr_language": language,
            "ocr_engine": None,
            "ocr_error": None,
            "ocr_text_length": 0,
            "ocr_extracted_text_length": 0,
            "ocr_chunk_count": 0,
            "ocr_chunks": [],
            "ocr_failed_chunks": [],
        }

    if not shutil.which("tesseract"):
        return {
            "ocr_requested": True,
            "ocr_applied": False,
            "ocr_status": "skipped",
            "ocr_language": language,
            "ocr_engine": None,
            "ocr_error": "tesseract command not found",
            "ocr_text_length": 0,
            "ocr_extracted_text_length": 0,
            "ocr_chunk_count": 0,
            "ocr_chunks": [],
            "ocr_failed_chunks": [],
        }

    try:
        ocr_result = ocr_image_chunks(png_path, language=language)
        inserted_words = add_invisible_text_layer_to_pdf(
            pdf_path,
            ocr_result["words"],
            image_width=image_width,
            image_height=image_height,
        )
        extracted_text_length = extract_pdf_text_length(pdf_path)
        expected_min = max(20, int(ocr_result["text_length"] * 0.35))
        applied = inserted_words > 0 and extracted_text_length >= expected_min
        return {
            "ocr_requested": True,
            "ocr_applied": applied,
            "ocr_status": "applied" if applied else "insufficient_text",
            "ocr_language": language,
            "ocr_engine": "tesseract-tsv+pypdf-text-layer",
            "ocr_error": None if applied else "OCR text layer extraction was below threshold",
            "ocr_text_length": ocr_result["text_length"],
            "ocr_extracted_text_length": extracted_text_length,
            "ocr_inserted_words": inserted_words,
            "ocr_chunk_count": len(ocr_result["chunks"]),
            "ocr_chunks": ocr_result["chunks"],
            "ocr_failed_chunks": ocr_result["failed_chunks"],
        }
    except Exception as exc:
        return {
            "ocr_requested": True,
            "ocr_applied": False,
            "ocr_status": "failed",
            "ocr_language": language,
            "ocr_engine": "tesseract-tsv+pypdf-text-layer",
            "ocr_error": str(exc),
            "ocr_text_length": 0,
            "ocr_extracted_text_length": extract_pdf_text_length(pdf_path) if Path(pdf_path).exists() else 0,
            "ocr_inserted_words": 0,
            "ocr_chunk_count": 0,
            "ocr_chunks": [],
            "ocr_failed_chunks": [],
        }

def crop_png_to_content_area(
    png_path: str,
    content_box: dict,
    output_width: int,
    coordinate_scale: int = 1,
    min_side_margin: int = PDF_MIN_SIDE_MARGIN_PX,
    min_bottom_margin: int = PDF_MIN_BOTTOM_MARGIN_PX,
) -> dict:
    from collections import Counter
    from PIL import Image, ImageChops

    with Image.open(png_path) as image:
        if image.mode in ("RGBA", "LA"):
            background = Image.new("RGBA", image.size, (*PDF_BACKGROUND_COLOR, 255))
            background.alpha_composite(image.convert("RGBA"))
            source = background.convert("RGB")
        else:
            source = image.convert("RGB")

    source_width, source_height = source.size

    sample_points = []
    for x in range(0, source_width, max(1, source_width // 16)):
        sample_points.append((x, 0))
        sample_points.append((x, source_height - 1))
    for y in range(0, source_height, max(1, source_height // 32)):
        sample_points.append((0, y))
        sample_points.append((source_width - 1, y))

    def quantized(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
        return tuple((channel // 8) * 8 for channel in pixel)

    bg_bucket = Counter(quantized(source.getpixel(point)) for point in sample_points).most_common(1)[0][0]
    bg_color = PDF_BACKGROUND_COLOR

    def is_content_pixel(pixel: tuple[int, int, int]) -> bool:
        return sum(abs(pixel[i] - bg_color[i]) for i in range(3)) > 36

    def measure_content_bounds(image: Image.Image) -> dict:
        image_width, image_height = image.size
        background = Image.new("RGB", image.size, bg_color)
        bbox = ImageChops.difference(image, background).getbbox()
        if not bbox:
            return {"left": image_width, "right": -1, "bottom": -1}
        left, _top, right, bottom = bbox
        return {"left": left, "right": right - 1, "bottom": bottom - 1}

    source_bounds = measure_content_bounds(source)
    pixel_left = source_bounds["left"]
    pixel_right = source_bounds["right"]
    pixel_bottom = source_bounds["bottom"]
    if pixel_right < pixel_left or pixel_bottom < 0:
        pixel_left = max(0, min(int(content_box["left"] * coordinate_scale), source_width - 1))
        pixel_right = max(pixel_left, min(int(content_box["right"] * coordinate_scale) - 1, source_width - 1))
        pixel_bottom = max(0, min(int(content_box["bottom"] * coordinate_scale) - 1, source_height - 1))

    dom_left = max(0, min(int(content_box["left"] * coordinate_scale), source_width - 1))
    dom_right = max(dom_left, min(int(content_box["right"] * coordinate_scale) - 1, source_width - 1))
    left_before = pixel_left
    right_before = source_width - pixel_right - 1

    content_left = min(pixel_left, dom_left)
    content_right = max(pixel_right, dom_right)
    content_width = content_right - content_left + 1
    scaled_bottom_margin = min_bottom_margin * coordinate_scale
    scaled_side_margin = min_side_margin * coordinate_scale
    bottom = max(1, min(pixel_bottom + 1 + scaled_bottom_margin, source_height))

    if content_width + (scaled_side_margin * 2) <= output_width:
        final_content_left = (output_width - content_width) // 2
        final_content_right = final_content_left + content_width
        crop_left = content_left
        crop_right = content_right + 1
        paste_x = final_content_left
    else:
        crop_left = max(0, min(content_left, source_width - output_width))
        crop_right = min(source_width, crop_left + output_width)
        paste_x = 0
        final_content_left = content_left - crop_left
        final_content_right = content_right - crop_left + 1

    cropped = source.crop((crop_left, 0, crop_right, bottom))
    cropped_width, cropped_height = cropped.size
    final = Image.new("RGB", (output_width, cropped_height), bg_color)
    final.paste(cropped, (paste_x, 0))

    final_bounds = measure_content_bounds(final)
    final_left_margin = max(0, final_bounds["left"])
    final_right_margin = max(0, output_width - final_bounds["right"] - 1)
    rebalance_shift_x = 0
    if final_bounds["right"] >= final_bounds["left"] and abs(final_left_margin - final_right_margin) >= 5:
        actual_content_width = final_bounds["right"] - final_bounds["left"] + 1
        if actual_content_width < output_width:
            centered_x = (output_width - actual_content_width) // 2
            rebalance_shift_x = centered_x - final_bounds["left"]
            content_only = final.crop((final_bounds["left"], 0, final_bounds["right"] + 1, cropped_height))
            rebalanced = Image.new("RGB", (output_width, cropped_height), bg_color)
            rebalanced.paste(content_only, (centered_x, 0))
            final = rebalanced
            final_bounds = measure_content_bounds(final)
            final_left_margin = max(0, final_bounds["left"])
            final_right_margin = max(0, output_width - final_bounds["right"] - 1)

    final.save(png_path)

    return {
        "original_image_width": source_width,
        "original_image_height": source_height,
        "cropped_image_width": output_width,
        "cropped_image_height": cropped_height,
        "removed_bottom_margin_px": source_height - cropped_height,
        "left_margin_before_px": left_before,
        "right_margin_before_px": right_before,
        "left_margin_px": final_left_margin,
        "right_margin_px": final_right_margin,
        "left_margin_after_px": final_left_margin,
        "right_margin_after_px": final_right_margin,
        "pdf_image_x": 0,
        "pdf_image_placement": "x=0 (image width equals PDF page width)",
        "content_box_left": final_bounds["left"],
        "content_box_right": final_bounds["right"] + 1,
        "content_box_bottom": int(content_box["bottom"] * coordinate_scale),
        "pixel_content_bottom": pixel_bottom + 1,
        "background_rgb": f"{bg_color[0]},{bg_color[1]},{bg_color[2]}",
        "image_crop_left_px": crop_left,
        "image_crop_right_px": crop_right,
        "image_paste_x_px": paste_x,
        "image_rebalance_shift_x_px": rebalance_shift_x,
        "image_coordinate_scale": coordinate_scale,
    }

def save_screenshot_as_single_page_pdf(
    page,
    output_path: str,
    width: int = PDF_WIDTH_PX,
    scale: int = 2,
    ocr: bool = True,
    text_layer_mode: str | None = None,
) -> dict:
    import img2pdf

    scale = max(1, min(int(scale), 3))
    png_path = str(OUTPUT_PNG_FOLDER / f"{Path(output_path).stem}.png")
    render_stability = wait_for_page_render_stability(page)
    safety_style_info = apply_capture_safety_styles(page)
    page.wait_for_timeout(250)
    initial_metrics = get_page_height_metrics(page)
    capture_height = max(initial_metrics["max_height"], 1080)
    viewport_height = min(capture_height, PDF_SCREENSHOT_CHUNK_HEIGHT_PX)
    page.set_viewport_size({"width": width, "height": max(1080, viewport_height)})
    page.wait_for_timeout(250)

    final_metrics = get_page_height_metrics(page)
    content_box = get_content_box_metrics(page)
    first_visible_info = get_first_visible_content_info(page)
    try:
        preprocess_info = page.evaluate("() => window.__notionPdfPreprocessResult || {}")
    except Exception:
        preprocess_info = {}
    print(
        "NOTION_CAPTURE_TOP="
        f"content_top:{first_visible_info.get('content_top')},"
        f"crop_top:{first_visible_info.get('crop_top')},"
        f"first_visible_text:{first_visible_info.get('first_visible_text')},"
        f"first_visible_text_y:{first_visible_info.get('first_visible_text_y')}"
    )
    capture_height = max(initial_metrics["max_height"], final_metrics["max_height"], content_box["bottom"] + PDF_MIN_BOTTOM_MARGIN_PX, 1080)
    viewport_height = min(capture_height, PDF_SCREENSHOT_CHUNK_HEIGHT_PX)
    page.set_viewport_size({"width": width, "height": max(1080, viewport_height)})
    page.wait_for_timeout(250)
    content_box = get_content_box_metrics(page)
    capture_height = max(capture_height, content_box["bottom"] + PDF_MIN_BOTTOM_MARGIN_PX)
    dom_text_items = get_dom_text_layer_items(page)
    clipping_debug_path = DEBUG_OUTPUT_FOLDER / f"{Path(output_path).stem}_clipping_blocks.json"
    clipping_blocks = log_potential_clipping_blocks(page, str(clipping_debug_path))
    chunk_info = capture_page_to_png_chunks(
        page,
        png_path,
        width=width,
        height=capture_height,
        chunk_height=PDF_SCREENSHOT_CHUNK_HEIGHT_PX,
        scale=scale,
    )

    original_image_width, original_image_height = get_png_size(png_path)
    expected_height = max(final_metrics["max_height"], capture_height)
    height_difference = max(0, expected_height - original_image_height)
    allowed_tolerance = max(PDF_HEIGHT_TOLERANCE_PX, (expected_height + 99) // 100)
    if height_difference > allowed_tolerance:
        raise RuntimeError(
            f"Screenshot is shorter than measured content. "
            f"DOM={final_metrics['dom_scroll_height']}, BODY={final_metrics['body_scroll_height']}, "
            f"WRAPPER={final_metrics['content_wrapper_scroll_height']}, "
            f"PNG={original_image_width}x{original_image_height}, EXPECTED_HEIGHT={expected_height}, "
            f"DIFF={height_difference}, TOLERANCE={allowed_tolerance}"
        )
    output_image_width = width * scale
    crop_metrics = crop_png_to_content_area(
        png_path,
        content_box,
        output_image_width,
        coordinate_scale=scale,
    )
    image_width, image_height = get_png_size(png_path)
    debug_png_path = DEBUG_OUTPUT_FOLDER / "debug_fullpage.png"
    shutil.copyfile(png_path, debug_png_path)
    pdf_width = width
    pdf_height = image_height * (pdf_width / image_width)
    layout_fun = img2pdf.get_layout_fun((pdf_width, pdf_height))
    with open(output_path, "wb") as fp:
        fp.write(img2pdf.convert(png_path, layout_fun=layout_fun))

    mode = normalize_text_layer_mode(text_layer_mode, ocr)
    text_layer_info = apply_text_layers_to_pdf(
        output_path,
        png_path,
        image_width=image_width,
        image_height=image_height,
        mode=mode,
        dom_items=dom_text_items,
        crop_metrics=crop_metrics,
    )
    page_count = assert_single_page_pdf(output_path)
    pdf_info = get_pdf_page_info(output_path)
    pdf_ratio = pdf_info["pdf_page_height"] / max(pdf_info["pdf_page_width"], 1)
    image_ratio = image_height / max(image_width, 1)
    if abs(pdf_ratio - image_ratio) > 0.02:
        raise RuntimeError(
            f"PDF ratio does not match screenshot ratio. "
            f"IMAGE={image_width}x{image_height}, PDF={pdf_info['pdf_page_width']}x{pdf_info['pdf_page_height']}"
        )
    result = {
        "pages": page_count,
        "dom_scroll_height": final_metrics["dom_scroll_height"],
        "body_scroll_height": final_metrics["body_scroll_height"],
        "content_wrapper_scroll_height": final_metrics["content_wrapper_scroll_height"],
        "max_element_bottom": final_metrics["max_element_bottom"],
        "capture_height": capture_height,
        "expected_height": expected_height,
        "height_difference": height_difference,
        "allowed_tolerance": allowed_tolerance,
        "scale": scale,
        "render_stability": render_stability,
        "preprocess": preprocess_info,
        "banner_detected_count": (preprocess_info.get("banner_cleanup") or {}).get("detected_count", 0),
        "banner_removed_count": (preprocess_info.get("banner_cleanup") or {}).get("removed_count", 0),
        "banner_boxes": (preprocess_info.get("banner_cleanup") or {}).get("removed")
        or (preprocess_info.get("banner_cleanup") or {}).get("detected", []),
        **first_visible_info,
        "capture_safety_adjusted": safety_style_info.get("adjusted", 0),
        "clipping_debug_path": str(clipping_debug_path),
        "clipping_debug_blocks": len(clipping_blocks),
        **chunk_info,
        **text_layer_info,
        "dom_text_nodes": len(dom_text_items),
        "original_image_width": original_image_width,
        "original_image_height": original_image_height,
        "image_width": image_width,
        "image_height": image_height,
        **crop_metrics,
        "final_image_width": image_width,
        "final_image_height": image_height,
        "pdf_page_width": pdf_info["pdf_page_width"],
        "pdf_page_height": pdf_info["pdf_page_height"],
        "pdf_file_size": Path(output_path).stat().st_size,
        "debug_png_path": str(debug_png_path),
        "pdf_path": output_path,
        "png_path": png_path,
    }
    print(
        f"PDF 생성 완료: PAGES={page_count}, "
        f"IMAGE={image_width}x{image_height}, PDF={output_path}"
    )
    return result

def html_to_seamless_pdf(
    html_content: str,
    output_path: str,
    width: int = 794,
    margin: int = 40,
    scale: int = 2,
    ocr: bool = True,
    text_layer_mode: str | None = None,
    expand_toggles: bool = True,
    remove_banners: bool = True,
):
    """Convert HTML to a single-page (no page breaks) PDF using Playwright."""
    from playwright.sync_api import sync_playwright

    pdf_width = PDF_WIDTH_PX
    css_inject = f"""
    <style>
    html, body {{ margin: 0 !important; min-height: 100% !important; background: #fff !important; }}
    body {{ width: {pdf_width}px !important; max-width: {pdf_width}px !important; margin: 0 auto !important; padding: {margin}px !important; padding-bottom: {margin + PDF_EXTRA_HEIGHT_PX}px !important; box-sizing: border-box !important; background: #fff !important; }}
    img {{ max-width: 100% !important; }}
    </style>
    """
    # Inject CSS before </head>
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', css_inject + '</head>')
    else:
        html_content = css_inject + html_content

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": pdf_width, "height": 1080},
            device_scale_factor=max(1, min(int(scale), 3)),
        )
        page.set_content(html_content, wait_until="networkidle")
        preprocess_page_before_capture(
            page,
            expand_toggles=expand_toggles,
            remove_banners=remove_banners,
            debug_stem=Path(output_path).stem,
        )
        result = save_screenshot_as_single_page_pdf(page, output_path, pdf_width, scale, ocr, text_layer_mode)
        browser.close()
        return result

def url_to_seamless_pdf(
    url: str,
    output_path: str,
    width: int = 794,
    margin: int = 40,
    scale: int = 2,
    ocr: bool = True,
    text_layer_mode: str | None = None,
    expand_toggles: bool = True,
    remove_banners: bool = True,
):
    """Fetch Notion URL and convert to seamless PDF."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

    pdf_width = PDF_WIDTH_PX
    with sync_playwright() as p:
        browser = None
        page = None
        stage = "브라우저 시작"
        status = "확인 전"

        try:
            browser = p.chromium.launch()
            page = browser.new_page(
                viewport={"width": pdf_width, "height": 1080},
                device_scale_factor=max(1, min(int(scale), 3)),
            )

            stage = "URL 접속"
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if response:
                status = f"HTTP {response.status}"
                if response.status >= 400:
                    raise RuntimeError(f"URL 접근 실패: {status}")
            else:
                status = "응답 없음"

            stage = "페이지 load 상태 대기"
            try:
                page.wait_for_load_state("load", timeout=60000)
            except PlaywrightTimeoutError:
                # Notion can keep loading background resources. DOM is already ready, so continue.
                pass

            stage = "Notion 렌더링 대기"
            page.wait_for_timeout(5000)

            stage = "Notion 캡처 전처리"
            preprocess_page_before_capture(
                page,
                expand_toggles=expand_toggles,
                remove_banners=remove_banners,
                debug_stem=Path(output_path).stem,
            )

            stage = "PDF 스타일 적용"
            page.add_style_tag(content=f"""
                html, body {{ margin: 0 !important; min-height: 100% !important; background: #fff !important; }}
                body {{ width: {pdf_width}px !important; max-width: {pdf_width}px !important; padding: {margin}px !important; padding-bottom: {margin + PDF_EXTRA_HEIGHT_PX}px !important; box-sizing: border-box !important; background: #fff !important; }}
                img {{ max-width: 100% !important; }}
            """)

            stage = "전체 페이지 PNG 캡처 및 PDF 생성"
            return save_screenshot_as_single_page_pdf(page, output_path, pdf_width, scale, ocr, text_layer_mode)
        except Exception as e:
            raise RuntimeError(
                f"Notion URL 변환 실패 ({stage}). URL: {url}. 접근 상태: {status}. "
                f"페이지가 공개되어 있는지, 브라우저에서 직접 열리는지 확인해주세요. 원인: {e}"
            ) from e
        finally:
            if browser:
                browser.close()

# ─── Routes ──────────────────────────────────────────────────
@app.route('/')
def index():
    return HTML_PAGE

@app.route('/convert/url', methods=['POST'])
def convert_url():
    data = request.json
    url = data.get('url', '').strip()
    width = int(data.get('width', 794))
    margin = int(data.get('margin', 40))
    scale = int(data.get('scale', 2))
    ocr = parse_bool(data.get('ocr'), True)
    text_layer_mode = normalize_text_layer_mode(data.get('text_layer_mode'), ocr)
    expand_toggles = parse_bool(data.get('expand_toggles'), True)
    remove_banners = parse_bool(data.get('remove_banners'), True)
    client_ip = get_client_ip()

    if not url.startswith('http'):
        safe_record_conversion(
            source_type="url",
            source_url=url,
            page_width=width,
            margin=margin,
            quality_scale=scale,
            text_layer_mode=text_layer_mode,
            status="failed",
            error_message="invalid url",
            client_ip=client_ip,
        )
        return jsonify({'error': '올바른 URL을 입력해주세요.'}), 400

    job_id = make_job_id()
    jobs[job_id] = {'status': 'processing', 'filename': None, 'path': None, 'error': None}

    def run():
        output_filename = None
        out = None
        try:
            output_filename, out = make_timestamped_pdf_path(job_id)
            result = url_to_seamless_pdf(url, out, width, margin, scale, ocr, text_layer_mode, expand_toggles, remove_banners)
            txt_path = extract_pdf_text_to_file(out)
            safe_record_conversion(
                source_type="url",
                source_url=url,
                output_pdf_path=out,
                output_txt_path=txt_path,
                output_png_path=result.get("png_path"),
                page_width=width,
                margin=margin,
                quality_scale=scale,
                text_layer_mode=text_layer_mode,
                status="success",
                file_size=Path(out).stat().st_size if Path(out).exists() else None,
                client_ip=client_ip,
            )
            jobs[job_id] = {'status': 'done', 'filename': output_filename, 'path': out, 'error': None, **result}
        except Exception as e:
            safe_record_conversion(
                source_type="url",
                source_url=url,
                output_pdf_path=out,
                page_width=width,
                margin=margin,
                quality_scale=scale,
                text_layer_mode=text_layer_mode,
                status="failed",
                error_message=str(e),
                client_ip=client_ip,
            )
            jobs[job_id] = {'status': 'error', 'filename': None, 'path': None, 'error': str(e)}

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/convert/file', methods=['POST'])
def convert_file():
    f = request.files.get('file')
    width = int(request.form.get('width', 794))
    margin = int(request.form.get('margin', 40))
    scale = int(request.form.get('scale', 2))
    ocr = parse_bool(request.form.get('ocr'), True)
    text_layer_mode = normalize_text_layer_mode(request.form.get('text_layer_mode'), ocr)
    expand_toggles = parse_bool(request.form.get('expand_toggles'), True)
    remove_banners = parse_bool(request.form.get('remove_banners'), True)
    client_ip = get_client_ip()

    if not f:
        safe_record_conversion(
            source_type="html_upload",
            page_width=width,
            margin=margin,
            quality_scale=scale,
            text_layer_mode=text_layer_mode,
            status="failed",
            error_message="missing file",
            client_ip=client_ip,
        )
        return jsonify({'error': '파일이 없습니다.'}), 400

    filename = f.filename or ""
    job_id = make_job_id()
    jobs[job_id] = {'status': 'processing', 'filename': None, 'path': None, 'error': None}

    ext = Path(filename).suffix.lower()
    if not allowed_upload_extension(filename):
        safe_record_conversion(
            source_type="html_upload",
            input_original_name=filename,
            original_filename=filename,
            page_width=width,
            margin=margin,
            quality_scale=scale,
            text_layer_mode=text_layer_mode,
            status="failed",
            error_message=f"unsupported file extension: {ext}",
            client_ip=client_ip,
        )
        return jsonify({'error': '지원하지 않는 파일 형식입니다.'}), 400

    stored_input_name, in_path = make_uploaded_input_path(job_id, filename)
    f.save(in_path)
    input_file_size = Path(in_path).stat().st_size if Path(in_path).exists() else None

    def run():
        output_filename = None
        out = None
        try:
            stem = Path(filename).stem or "notion_export"
            output_filename, out = make_timestamped_pdf_path(job_id, f"{stem}_seamless")
            if ext in ('.html', '.htm'):
                with open(in_path, 'r', encoding='utf-8', errors='ignore') as fp:
                    html = fp.read()
                result = html_to_seamless_pdf(html, out, width, margin, scale, ocr, text_layer_mode, expand_toggles, remove_banners)
            elif ext == '.pdf':
                # PDF → re-render as single page via html wrapper trick
                # Just copy with a note (full re-render from PDF is complex)
                raise RuntimeError("PDF upload is not supported for screenshot-based single-page regeneration. Use a Notion URL or HTML file.")
            else:
                raise RuntimeError(f"지원하지 않는 파일 형식입니다: {ext}")
            txt_path = extract_pdf_text_to_file(out)
            safe_record_conversion(
                source_type="html_upload",
                original_filename=filename,
                input_original_name=filename,
                input_file_path=in_path,
                input_file_size=input_file_size,
                output_pdf_path=out,
                output_txt_path=txt_path,
                output_png_path=result.get("png_path"),
                page_width=width,
                margin=margin,
                quality_scale=scale,
                text_layer_mode=text_layer_mode,
                status="success",
                file_size=Path(out).stat().st_size if Path(out).exists() else None,
                client_ip=client_ip,
            )
            jobs[job_id] = {'status': 'done', 'filename': output_filename, 'path': out, 'error': None, **result}
        except Exception as e:
            safe_record_conversion(
                source_type="html_upload",
                original_filename=filename,
                input_original_name=filename,
                input_file_path=in_path,
                input_file_size=input_file_size,
                output_pdf_path=out,
                page_width=width,
                margin=margin,
                quality_scale=scale,
                text_layer_mode=text_layer_mode,
                status="failed",
                error_message=str(e),
                file_size=Path(out).stat().st_size if out and Path(out).exists() else None,
                client_ip=client_ip,
            )
            jobs[job_id] = {'status': 'error', 'filename': None, 'path': None, 'error': str(e)}

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/job/<job_id>')
def job_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'error': '잘못된 작업 ID'}), 404
    return jsonify(job)

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return "Not found", 404
    return send_file(job['path'], as_attachment=True, download_name=job['filename'])

@app.route('/admin/conversions/<int:conversion_id>/download/<file_kind>')
def admin_download_conversion_file(conversion_id, file_kind):
    if not is_authorized_admin_request():
        return "Forbidden", 403
    row = get_conversion(conversion_id)
    if not row:
        return "Not found", 404
    path_fields = {
        "input": "input_file_path",
        "pdf": "output_pdf_path",
        "txt": "output_txt_path",
        "png": "output_png_path",
    }
    field = path_fields.get(file_kind)
    if not field:
        return "Not found", 404
    path_value = row.get(field)
    if not file_path_is_allowed(path_value):
        return "Not found", 404
    path = Path(path_value).resolve()
    if not path.exists() or not path.is_file():
        return "Not found", 404
    return send_file(path, as_attachment=True, download_name=path.name)

@app.route('/admin/conversions')
def admin_conversions():
    try:
        rows = list_recent_conversions(limit=100)
    except Exception as exc:
        return f"DB error: {exc}", 500
    return render_template_string(
        """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>notion_pdf conversions</title>
  <style>
    body { font-family: sans-serif; margin: 24px; color: #111; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }
    th { background: #f6f6f6; text-align: left; }
    .success { color: #047857; font-weight: 700; }
    .failed { color: #b91c1c; font-weight: 700; }
    .path { max-width: 280px; word-break: break-all; }
  </style>
</head>
<body>
  <h1>최근 변환 내역</h1>
  <p>최대 100건을 표시합니다. 이 페이지는 로컬/터널 접근 권한이 있는 관리자 확인용입니다.</p>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Created</th><th>Source</th><th>Status</th><th>Mode</th>
        <th>Input</th><th>PDF</th><th>TXT</th><th>PNG</th><th>Size</th><th>IP</th><th>Expires</th><th>Error</th>
      </tr>
    </thead>
    <tbody>
    {% for row in rows %}
      <tr>
        <td>{{ row.id }}</td>
        <td>{{ row.created_at }}</td>
        <td>{{ row.source_type }}<br>{{ row.source_url or row.original_filename or "" }}</td>
        <td class="{{ row.status }}">{{ row.status }}</td>
        <td>{{ row.text_layer_mode }}</td>
        <td class="path">
          {{ row.input_original_name or row.original_filename or "" }}<br>
          {% if row.input_file_path %}<a href="/admin/conversions/{{ row.id }}/download/input">원본 다운로드</a><br>{{ row.input_file_path }}{% endif %}
        </td>
        <td class="path">
          {% if row.output_pdf_path %}<a href="/admin/conversions/{{ row.id }}/download/pdf">PDF 다운로드</a><br>{{ row.output_pdf_path }}{% endif %}
        </td>
        <td class="path">
          {% if row.output_txt_path %}<a href="/admin/conversions/{{ row.id }}/download/txt">TXT 다운로드</a><br>{{ row.output_txt_path }}{% endif %}
        </td>
        <td class="path">
          {% if row.output_png_path %}<a href="/admin/conversions/{{ row.id }}/download/png">PNG 다운로드</a><br>{{ row.output_png_path }}{% endif %}
        </td>
        <td>{{ row.file_size or "" }}</td>
        <td>{{ row.client_ip or "" }}</td>
        <td>{{ row.expires_at }}</td>
        <td>{{ row.error_message or "" }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</body>
</html>""",
        rows=rows,
    )

if __name__ == '__main__':
    print("서버 시작: http://localhost:5000")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False")
    print(f"Server URL: http://localhost:{port}")
    app.run(host="127.0.0.1", debug=debug, port=port, threaded=True)
