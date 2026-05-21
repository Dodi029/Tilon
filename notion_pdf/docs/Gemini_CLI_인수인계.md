# Gemini CLI 인수인계

작성일: 2026-05-17

## 프로젝트 경로

```text
Mac: ~/git/dev/projects/Tilon/notion_pdf
Windows: C:\dev\projects\Tilon\notion_pdf
```

## dev 폴더 구조

Mac:

```text
~/git/dev
├─ _template
├─ logs
├─ projects
│  └─ Tilon
│     └─ notion_pdf
├─ sandbox
├─ scripts
└─ vm
```

Windows:

```text
C:\dev
├─ projects
│  └─ Tilon
│     └─ notion_pdf
├─ logs
├─ sandbox
├─ scripts
└─ vm
```

## 현재 안정 기준

- `v3.0`은 안정 버전이다.
- `v3.1`은 실험 중 또는 복구 대상일 수 있다.
- 안정 기능은 `v3.0` 기준으로 유지해야 한다.

## 핵심 기능

- Notion URL 또는 HTML 파일 입력
- Playwright 렌더링
- `page.pdf()` 미사용
- `full_page=True` 의존 금지
- screenshot `clip` 기반 캡처
- PNG 기반 긴 1페이지 PDF 생성
- 하단 crop
- 좌우 여백 보정
- 고화질 캡처 옵션
- 텍스트 레이어 옵션
- Cloudflare Tunnel을 통한 외부 접근

## 금지사항

- `page.pdf()` 사용 금지
- `full_page=True`에만 의존 금지
- 기존 긴 1페이지 PDF 기능 깨뜨리기 금지
- `v3.0` 안정 기능보다 OCR 개선을 우선하지 말 것
- OCR/DOM 수정 시 PDF가 빈 페이지가 되면 즉시 중단
- 기능 깨짐 상태를 성공 처리하지 말 것
- 사용자 승인 전까지 git commit/push 금지

## 현재 해결 중인 문제

- Notion 상단 로그인/가입 배너 제거
- 일부 텍스트가 선택되지 않는 문제
- DOM 텍스트 레이어 누락 문제
- OCR/DOM 중복 삽입 시 복사 결과가 깨지는 문제
- Windows에서 Markdown 문서 한글 인코딩 깨짐 문제

## 테스트 명령

```bash
python -m py_compile app.py
python -m unittest discover -s tests
python tests/run_server_pdf_flow.py
python tests/run_ocr_comparison.py
python tests/run_banner_text_validation.py
rg "page\.pdf|full_page=True" app.py tests
```

## 서버 실행

```bash
source .venv/bin/activate
python app.py
```

접속:

```text
http://127.0.0.1:5000
```

## Cloudflare Tunnel

```bash
cloudflared tunnel --url http://127.0.0.1:5000
```

출력된 `https://xxxxx.trycloudflare.com` 주소를 외부 사용자에게 전달한다.
Flask 서버와 `cloudflared` 터미널 둘 다 켜져 있어야 한다.

## Gemini CLI 시작 프롬프트

아래 내용을 그대로 붙여넣고 시작한다.

```text
이 프로젝트는 Codex에서 작업하던 notion_pdf 프로젝트다.
현재 작업 경로는 ~/git/dev/projects/Tilon/notion_pdf 이다.

먼저 아래 문서를 모두 읽고 현재 상태를 파악해라.

- docs/현재상태.md
- docs/작업로그.md
- docs/테스트결과.md
- docs/세션복원가이드.md
- docs/AI작업인수인계.md
- docs/Gemini_CLI_인수인계.md
- README.md

중요:
v3.0은 안정 버전이다.
긴 1페이지 PDF 생성 기능을 절대 깨뜨리지 마라.
page.pdf()는 사용하지 마라.
full_page=True에만 의존하지 마라.
OCR/DOM 텍스트 레이어 개선보다 PDF 생성 안정성을 우선해라.

v3.5 기준 추가 기능:
- Notion 토글 자동 펼치기 옵션은 기본 켜짐이다.
- Notion 상단 로그인/가입 배너 제거 옵션은 기본 켜짐이다.
- 두 기능은 캡처 전 Playwright DOM 전처리로 수행한다.
- 전처리 실패 시 PDF 생성은 계속되어야 한다.

v3.6 기준 추가 기능:
- 긴 페이지는 chunk 단위로 캡처한 뒤 하나의 긴 PNG로 stitch한다.
- `page.pdf()`와 `full_page=True`는 계속 사용 금지다.
- table/database 이미지 잘림 완화를 위해 이미지 로딩 대기와 overflow clipping 완화 스타일을 적용한다.
- chunk/debug 로그는 `output/debug/`에 남긴다.

v3.7 기준 추가 기능:
- Notion 서비스 배너 제거 조건을 정확한 배너 문구 중심으로 축소했다.
- 단독 `Sign up`, `login` 또는 모든 `header/nav/fixed/sticky` 요소를 광범위하게 제거하지 마라.
- 문서 제목/properties 영역(`TOS 점검 업무 매뉴얼`, `구분`, `날짜`, `작성자`, `속성`)은 캡처에 포함되어야 한다.
- 캡처 직전 `content_top`, `crop_top`, `first_visible_text`, `first_visible_text_y` 로그를 확인한다.
- 전처리 전/후 debug screenshot은 `output/debug/*_preprocess_before.png`, `output/debug/*_preprocess_after.png`에 저장된다.

현재 진행 중인 작업:
- Notion 상단 로그인/가입 배너 제거
- 선택되지 않는 본문 텍스트 줄이기
- DOM 텍스트 레이어 누락 개선
- Markdown 문서 UTF-8 인코딩 유지

작업 전 반드시 테스트를 먼저 실행하고,
작업 후에도 동일 테스트를 실행해라.

git commit/push는 사용자 승인 전까지 하지마.
```

## 처음 읽을 문서

- `docs/현재상태.md`
- `docs/작업로그.md`
- `docs/테스트결과.md`
- `docs/세션복원가이드.md`
- `docs/AI작업인수인계.md`
- `docs/Gemini_CLI_인수인계.md`
- `README.md`

## 문서 인코딩 정책

- 모든 Markdown 문서는 UTF-8이다.
- Windows에서도 깨지지 않아야 한다.
- `.gitattributes` 정책을 확인한다.
- `docs/*.md` UTF-8 읽기 테스트를 수행한다.

## 기록 정책

- 어떤 AI CLI가 작업하든 `docs/작업로그.md`에 기록한다.
- 테스트 결과는 `docs/테스트결과.md`에 기록한다.
- 현재 상태 변경은 `docs/현재상태.md`에 기록한다.
- 새 세션 인수인계 내용은 `docs/AI작업인수인계.md`에 기록한다.
