# Notion PDF 변환기

Notion HTML 파일 또는 공개 URL을 긴 1페이지 PDF로 변환하는 로컬 Flask 앱입니다. A4 폭 기준인 794px에 맞춰 전체 페이지를 Playwright로 렌더링하고, `page.pdf()`가 아니라 전체 페이지 PNG 스크린샷을 만든 뒤 `img2pdf`로 1페이지 PDF를 생성합니다.

현재 기본 권장 옵션은 `DOM + OCR`입니다. Notion DOM 원문 텍스트를 우선 사용하고, DOM으로 잡히지 않는 이미지 내부 텍스트만 OCR로 보조합니다.

## 설치

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

OCR 텍스트 레이어까지 넣으려면 로컬에 OCRmyPDF와 Tesseract 언어 데이터가 추가로 필요합니다. macOS 예시는 다음과 같습니다.

```bash
brew install ocrmypdf tesseract tesseract-lang
```

기본 OCR 언어는 `kor+eng`입니다. 필요하면 `OCR_LANG` 환경변수로 바꿀 수 있습니다.

## 서버 실행

```bash
python app.py
```

기본 접속 URL은 다음과 같습니다.

```text
http://localhost:5000
```

## 외부 공개

현재 개발 환경에서는 Cloudflare Tunnel로 Mac mini의 로컬 Flask 서버를 외부 HTTPS 주소로 임시 공개할 수 있습니다.

```bash
cloudflared tunnel --url http://127.0.0.1:5000
```

성공하면 `https://xxxxx.trycloudflare.com` 형식의 주소가 표시되며, 다른 PC나 외부 사용자에게 이 주소를 전달해 접속할 수 있습니다. 자세한 절차는 `docs/배포가이드.md`를 참고하세요.

## Windows 문서 인코딩

이 프로젝트의 Markdown/TXT 문서는 UTF-8 기준입니다. Windows에서 한글 문서가 깨져 보이면 편집기 인코딩을 `UTF-8`로 열었는지 확인하세요.

Git 체크아웃 정책은 `.gitattributes`에 기록되어 있습니다.

```text
*.md text working-tree-encoding=UTF-8 eol=lf
*.txt text working-tree-encoding=UTF-8 eol=lf
```

다른 포트를 쓰려면 `PORT` 환경변수를 지정합니다.

```powershell
$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py
```

## PDF 생성 방식

1. Flask 서버가 HTML 파일 업로드 또는 공개 URL을 받습니다.
2. Playwright Chromium이 페이지를 렌더링합니다.
3. A4 기준 폭 `794px`로 viewport와 본문 폭을 맞춥니다.
4. DOM, body, Notion wrapper 후보, 실제 element bottom 값을 모두 측정합니다.
5. 가장 큰 높이를 viewport와 screenshot `clip.height`에 명시해 전체 높이 PNG를 캡처합니다.
6. PNG 높이가 expected height보다 작아도 `max(150px, expected height의 1%)` 안이면 정상으로 처리합니다.
7. 실제 콘텐츠 bounding box를 기준으로 PNG 하단 빈 공간을 제거합니다.
8. 좌우 여백이 같아지도록 콘텐츠를 A4 폭 안에서 중앙 정렬합니다.
9. `img2pdf`가 보정된 PNG 크기 비율 그대로 1페이지 PDF로 변환합니다.
10. 기본값은 DOM 원문 우선 + OCR 보조 텍스트 레이어를 추가합니다.
11. DOM 텍스트 영역과 겹치는 OCR은 제외해 중복 텍스트 삽입을 줄입니다.
12. `pypdf`로 PDF 페이지 수가 반드시 1페이지인지 검증합니다.
13. PDF 페이지 크기 비율이 PNG 크기 비율과 맞는지 검증합니다.

## 테스트

단위 테스트:

```bash
python -m unittest discover -s tests
```

서버 실행, URL 접속 확인, HTML 업로드, PDF 생성, 다운로드, pypdf 1페이지 검증을 한 번에 수행:

```bash
python tests\run_server_pdf_flow.py
```

성공하면 `SERVER_URL`, `JOB_ID`, DOM/body/wrapper 높이, expected height, screenshot PNG height, height difference, allowed tolerance, 원본 PNG 크기, crop 후 PNG 크기, 제거된 하단 여백, 좌우 여백, PDF 페이지 수, PDF 페이지 크기, debug PNG 경로가 출력됩니다.

## 주의

- 공개 Notion URL은 브라우저에서 직접 열리는 상태여야 합니다.
- 공개 Notion 페이지의 상단 가입/로그인 유도 배너는 캡처 전에 숨깁니다.
- 텍스트 복사 결과가 원문과 다르면 DOM/OCR 중복 삽입 여부를 먼저 확인하세요.
- PDF 업로드를 다시 긴 1페이지로 재렌더링하는 기능은 현재 지원하지 않습니다. HTML 파일 또는 URL을 사용하세요.
- 생성 파일은 OS 임시 폴더 아래 `notion_pdf` 디렉터리에 저장됩니다.
