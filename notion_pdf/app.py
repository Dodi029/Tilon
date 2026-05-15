from flask import Flask, request, jsonify, send_file, render_template_string
import os, shutil, tempfile, time, threading
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / "notion_pdf"
UPLOAD_FOLDER.mkdir(exist_ok=True)
DEBUG_OUTPUT_FOLDER = Path(__file__).resolve().parent / "output"
DEBUG_OUTPUT_FOLDER.mkdir(exist_ok=True)

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
    grid-template-columns: 1fr 1fr 1fr;
    gap: 0.75rem;
    margin-bottom: 1.5rem;
  }

  .option-group label.label { margin-bottom: 0.4rem; }

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
      <label class="label">HTML 또는 PDF 파일</label>
      <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <div class="drop-icon">📂</div>
        <div class="drop-text">클릭하거나 <strong>파일을 여기에 드래그</strong>하세요<br><span style="font-size:0.75rem; margin-top:0.25rem; display:block">지원 형식: .html, .pdf</span></div>
      </div>
      <input type="file" id="fileInput" accept=".html,.htm,.pdf" onchange="handleFile(this)">
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
        body: JSON.stringify({ url, width: parseInt(width), margin: parseInt(margin), scale: parseInt(scale) })
      });
    } else {
      if (!selectedFile) { alert('파일을 선택해주세요.'); btn.disabled=false; return; }
      setProgress(20, '파일 업로드 중...');
      const fd = new FormData();
      fd.append('file', selectedFile);
      fd.append('width', width);
      fd.append('margin', margin);
      fd.append('scale', scale);
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

def make_job_id():
    import uuid
    return str(uuid.uuid4())[:8]

def make_timestamped_pdf_path(job_id: str, prefix: str = "notion_export") -> tuple[str, str]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}_{job_id}.pdf"
    return filename, str(UPLOAD_FOLDER / filename)

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
        const wrapperHeights = selectors.flatMap((selector) =>
            Array.from(document.querySelectorAll(selector)).map((el) => {
                const rect = el.getBoundingClientRect();
                return Math.ceil(Math.max(
                    el.scrollHeight || 0,
                    el.offsetHeight || 0,
                    rect.bottom + window.scrollY
                ));
            })
        );
        const elementBottoms = Array.from(document.body.querySelectorAll('*')).map((el) => {
            const rect = el.getBoundingClientRect();
            return Math.ceil(rect.bottom + window.scrollY);
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
            return {
                left: rect.left + window.scrollX,
                top: rect.top + window.scrollY,
                right: rect.right + window.scrollX,
                bottom: rect.bottom + window.scrollY
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
    if final_bounds["right"] >= final_bounds["left"] and abs(final_left_margin - final_right_margin) >= 5:
        actual_content_width = final_bounds["right"] - final_bounds["left"] + 1
        if actual_content_width < output_width:
            centered_x = (output_width - actual_content_width) // 2
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
    }

def save_screenshot_as_single_page_pdf(page, output_path: str, width: int = PDF_WIDTH_PX, scale: int = 1) -> dict:
    import img2pdf

    scale = max(1, min(int(scale), 3))
    png_path = str(Path(output_path).with_suffix(".png"))
    initial_metrics = get_page_height_metrics(page)
    capture_height = max(initial_metrics["max_height"], 1080)
    page.set_viewport_size({"width": width, "height": capture_height})
    page.wait_for_timeout(250)

    final_metrics = get_page_height_metrics(page)
    content_box = get_content_box_metrics(page)
    capture_height = max(initial_metrics["max_height"], final_metrics["max_height"], content_box["bottom"] + PDF_MIN_BOTTOM_MARGIN_PX, 1080)
    page.set_viewport_size({"width": width, "height": capture_height})
    page.wait_for_timeout(250)
    content_box = get_content_box_metrics(page)
    capture_height = max(capture_height, content_box["bottom"] + PDF_MIN_BOTTOM_MARGIN_PX)
    page.screenshot(
        path=png_path,
        type="png",
        clip={"x": 0, "y": 0, "width": width, "height": capture_height},
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

    Path(png_path).unlink(missing_ok=True)
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
    }
    print(
        f"PDF 생성 완료: PAGES={page_count}, "
        f"IMAGE={image_width}x{image_height}, PDF={output_path}"
    )
    return result

def html_to_seamless_pdf(html_content: str, output_path: str, width: int = 794, margin: int = 40, scale: int = 1):
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
        result = save_screenshot_as_single_page_pdf(page, output_path, pdf_width, scale)
        browser.close()
        return result

def url_to_seamless_pdf(url: str, output_path: str, width: int = 794, margin: int = 40, scale: int = 1):
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

            stage = "PDF 스타일 적용"
            page.add_style_tag(content=f"""
                html, body {{ margin: 0 !important; min-height: 100% !important; background: #fff !important; }}
                body {{ width: {pdf_width}px !important; max-width: {pdf_width}px !important; padding: {margin}px !important; padding-bottom: {margin + PDF_EXTRA_HEIGHT_PX}px !important; box-sizing: border-box !important; background: #fff !important; }}
                img {{ max-width: 100% !important; }}
            """)

            stage = "전체 페이지 PNG 캡처 및 PDF 생성"
            return save_screenshot_as_single_page_pdf(page, output_path, pdf_width, scale)
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

    if not url.startswith('http'):
        return jsonify({'error': '올바른 URL을 입력해주세요.'}), 400

    job_id = make_job_id()
    jobs[job_id] = {'status': 'processing', 'filename': None, 'path': None, 'error': None}

    def run():
        try:
            output_filename, out = make_timestamped_pdf_path(job_id)
            result = url_to_seamless_pdf(url, out, width, margin, scale)
            jobs[job_id] = {'status': 'done', 'filename': output_filename, 'path': out, 'error': None, **result}
        except Exception as e:
            jobs[job_id] = {'status': 'error', 'filename': None, 'path': None, 'error': str(e)}

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'job_id': job_id})

@app.route('/convert/file', methods=['POST'])
def convert_file():
    f = request.files.get('file')
    width = int(request.form.get('width', 794))
    margin = int(request.form.get('margin', 40))
    scale = int(request.form.get('scale', 2))

    if not f:
        return jsonify({'error': '파일이 없습니다.'}), 400

    filename = f.filename
    job_id = make_job_id()
    jobs[job_id] = {'status': 'processing', 'filename': None, 'path': None, 'error': None}

    ext = Path(filename).suffix.lower()
    in_path = str(UPLOAD_FOLDER / f"{job_id}_input{ext}")
    f.save(in_path)

    def run():
        try:
            stem = Path(filename).stem or "notion_export"
            output_filename, out = make_timestamped_pdf_path(job_id, f"{stem}_seamless")
            if ext in ('.html', '.htm'):
                with open(in_path, 'r', encoding='utf-8', errors='ignore') as fp:
                    html = fp.read()
                result = html_to_seamless_pdf(html, out, width, margin, scale)
            elif ext == '.pdf':
                # PDF → re-render as single page via html wrapper trick
                # Just copy with a note (full re-render from PDF is complex)
                raise RuntimeError("PDF upload is not supported for screenshot-based single-page regeneration. Use a Notion URL or HTML file.")
            else:
                raise RuntimeError(f"지원하지 않는 파일 형식입니다: {ext}")
            jobs[job_id] = {'status': 'done', 'filename': output_filename, 'path': out, 'error': None, **result}
        except Exception as e:
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

if __name__ == '__main__':
    print("서버 시작: http://localhost:5000")
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "1") not in ("0", "false", "False")
    print(f"Server URL: http://localhost:{port}")
    app.run(host="127.0.0.1", debug=debug, port=port, threaded=True)
