# Notion PDF 변환기

Notion HTML 파일 또는 공개 URL을 긴 1페이지 PDF로 변환하는 로컬 Flask 앱입니다. A4 폭 기준인 794px에 맞춰 전체 페이지를 Playwright로 렌더링하고, `page.pdf()`가 아니라 전체 페이지 PNG 스크린샷을 만든 뒤 `img2pdf`로 1페이지 PDF를 생성합니다.

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

최근 변환 내역은 SQLite에 저장됩니다.

```text
instance/notion_pdf.db
```

관리자 확인용 최근 변환 내역 페이지:

```text
http://localhost:5000/admin/conversions
```

이 페이지는 별도 인증이 없으므로 외부 공개 시 접근 범위를 신중히 관리해야 합니다.

## 외부 공개

현재 개발 환경에서는 Cloudflare Tunnel로 Mac mini의 로컬 Flask 서버를 외부 HTTPS 주소로 임시 공개할 수 있습니다.

```bash
cloudflared tunnel --url http://127.0.0.1:5000
```

성공하면 `https://xxxxx.trycloudflare.com` 형식의 주소가 표시되며, 다른 PC나 외부 사용자에게 이 주소를 전달해 접속할 수 있습니다. 자세한 절차는 `docs/배포가이드.md`를 참고하세요.

다른 포트를 쓰려면 `PORT` 환경변수를 지정합니다.

```powershell
$env:PORT=5055; $env:FLASK_DEBUG=0; python app.py
```

## 상시 실행

Mac mini에서 재부팅 후에도 자동 실행하려면 launchd 예시를 사용합니다.

```bash
chmod +x scripts/macos/start_flask.sh scripts/macos/start_cloudflare_quick_tunnel.sh
cp scripts/macos/com.notion_pdf.flask.plist ~/Library/LaunchAgents/
cp scripts/macos/com.notion_pdf.cloudflare.quick.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.notion_pdf.flask.plist
launchctl load ~/Library/LaunchAgents/com.notion_pdf.cloudflare.quick.plist
```

현재 예시는 quick tunnel 기준입니다. quick tunnel은 실행할 때마다 `trycloudflare.com` 임시 주소가 바뀔 수 있습니다. 고정 주소가 필요하면 Cloudflare named tunnel과 고정 도메인으로 확장해야 합니다.

## 자동 삭제

기본 보관 기간은 7일입니다. 만료된 DB 기록과 오래된 PDF/PNG/TXT 파일을 정리합니다.

수동 실행:

```bash
python cleanup_old_records.py
```

dry-run:

```bash
python cleanup_old_records.py --dry-run
```

하루 1회 자동 실행하려면 launchd 예시를 등록합니다.

```bash
cp scripts/macos/com.notion_pdf.cleanup.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.notion_pdf.cleanup.plist
```

정리 로그:

```text
logs/cleanup.log
```

## PDF 생성 방식

1. Flask 서버가 HTML 파일 업로드 또는 공개 URL을 받습니다.
2. Playwright Chromium이 페이지를 렌더링합니다.
3. 옵션이 켜져 있으면 닫힌 Notion 토글을 캡처 전에 자동으로 펼칩니다.
4. 옵션이 켜져 있으면 Notion 공개 페이지의 로그인/가입 상단 배너를 숨깁니다.
5. A4 기준 폭 `794px`로 viewport와 본문 폭을 맞춥니다.
6. DOM, body, Notion wrapper 후보, 실제 element bottom 값을 모두 측정합니다.
7. 가장 큰 높이를 viewport와 screenshot `clip.height`에 명시해 전체 높이 PNG를 캡처합니다.
8. PNG 높이가 expected height보다 작아도 `max(150px, expected height의 1%)` 안이면 정상으로 처리합니다.
9. 실제 콘텐츠 bounding box를 기준으로 PNG 하단 빈 공간을 제거합니다.
10. 좌우 여백이 같아지도록 콘텐츠를 A4 폭 안에서 중앙 정렬합니다.
11. `img2pdf`가 보정된 PNG 크기 비율 그대로 1페이지 PDF로 변환합니다.
12. OCR/DOM 옵션이 켜져 있으면 텍스트 레이어를 추가합니다.
13. `pypdf`로 PDF 페이지 수가 반드시 1페이지인지 검증합니다.
14. PDF 페이지 크기 비율이 PNG 크기 비율과 맞는지 검증합니다.

## Notion 전처리 옵션

기본값은 둘 다 켜짐입니다.

- Notion 토글 자동 펼치기: 닫혀 있는 Notion 토글을 캡처 전에 자동으로 펼쳐 내부 내용을 PDF에 포함합니다.
- Notion 상단 배너 제거: `You're almost there`, `Sign up or login` 같은 공개 페이지 로그인/가입 안내 배너를 캡처에서 제외합니다.

전처리 실패가 발생해도 PDF 생성 자체는 중단하지 않고 로그만 남깁니다. 토글로 판단되는 후보만 처리하지만, Notion DOM 구조가 바뀌면 일부 토글이 남을 수 있습니다.

## 테스트

단위 테스트:

```bash
python -m unittest discover -s tests
```

서버 실행, URL 접속 확인, HTML 업로드, PDF 생성, 다운로드, pypdf 1페이지 검증을 한 번에 수행:

```bash
python tests\run_server_pdf_flow.py
```

DB와 자동 삭제 검증:

```bash
python tests\run_db_cleanup_validation.py
```

성공하면 `SERVER_URL`, `JOB_ID`, DOM/body/wrapper 높이, expected height, screenshot PNG height, height difference, allowed tolerance, 원본 PNG 크기, crop 후 PNG 크기, 제거된 하단 여백, 좌우 여백, PDF 페이지 수, PDF 페이지 크기, debug PNG 경로가 출력됩니다.

## 주의

- 공개 Notion URL은 브라우저에서 직접 열리는 상태여야 합니다.
- PDF 업로드를 다시 긴 1페이지로 재렌더링하는 기능은 현재 지원하지 않습니다. HTML 파일 또는 URL을 사용하세요.
- 생성 파일은 OS 임시 폴더 아래 `notion_pdf` 디렉터리에 저장됩니다.
- 업로드 원본 파일은 `uploads/YYYY-MM/` 폴더에 저장됩니다.
- 변환 결과 PDF는 `output/pdf/` 폴더에 저장됩니다.
- 변환 결과 PNG는 `output/png/` 폴더에 저장됩니다.
- 변환 결과 TXT는 `output/txt/` 폴더에 저장됩니다.
- 디버그 이미지는 `output/debug/`, 검증 산출물은 `output/tests/`에 둡니다.
- DB에는 원본 파일 경로와 결과 파일 경로가 함께 기록됩니다.
- 관리자 페이지에서 원본, PDF, TXT, PNG 다운로드 링크를 확인할 수 있습니다.
- `uploads/`와 `output/` 파일은 직접 정적 공개하지 않고 관리자 다운로드 라우트를 통해 제공합니다.
- 파일명은 `YYYYMMDD_HHMMSS_원본이름_작업ID.ext` 형식을 사용합니다.
- 외부 공개 시 개인정보나 민감정보가 포함된 문서를 업로드하지 마세요.
- 업로드 제한은 기본 `MAX_UPLOAD_MB=50`입니다.
- Mac mini가 절전 모드로 들어가면 Flask 서버와 Cloudflare Tunnel 연결이 끊길 수 있습니다.
