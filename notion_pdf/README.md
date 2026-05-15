# Notion PDF 변환기

Notion HTML 파일 또는 공개 URL을 긴 1페이지 PDF로 변환하는 로컬 Flask 앱입니다. A4 폭 기준인 794px에 맞춰 전체 페이지를 Playwright로 렌더링하고, `page.pdf()`가 아니라 전체 페이지 PNG 스크린샷을 만든 뒤 `img2pdf`로 1페이지 PDF를 생성합니다.

## 설치

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## 서버 실행

```bash
python app.py
```

기본 접속 URL은 다음과 같습니다.

```text
http://localhost:5000
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
6. PNG 높이가 측정된 콘텐츠 높이보다 짧으면 실패 처리합니다.
7. `img2pdf`가 PNG 크기 비율 그대로 1페이지 PDF로 변환합니다.
8. `pypdf`로 PDF 페이지 수가 반드시 1페이지인지 검증합니다.
9. PDF 페이지 크기 비율이 PNG 크기 비율과 맞는지 검증합니다.

## 테스트

단위 테스트:

```bash
python -m unittest discover -s tests
```

서버 실행, URL 접속 확인, HTML 업로드, PDF 생성, 다운로드, pypdf 1페이지 검증을 한 번에 수행:

```bash
python tests\run_server_pdf_flow.py
```

성공하면 `SERVER_URL`, `JOB_ID`, DOM/body/wrapper 높이, PNG 크기, PDF 페이지 수, PDF 페이지 크기, debug PNG 경로가 출력됩니다.

## 주의

- 공개 Notion URL은 브라우저에서 직접 열리는 상태여야 합니다.
- PDF 업로드를 다시 긴 1페이지로 재렌더링하는 기능은 현재 지원하지 않습니다. HTML 파일 또는 URL을 사용하세요.
- 생성 파일은 OS 임시 폴더 아래 `notion_pdf` 디렉터리에 저장됩니다.
