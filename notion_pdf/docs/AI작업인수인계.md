# AI 작업 인수인계

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

## 안정 기준

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
- 텍스트 레이어 옵션: `none`, `ocr`, `dom`, `hybrid`
- Cloudflare Tunnel을 통한 외부 접근
- SQLite 변환 이력 저장: `instance/notion_pdf.db`
- 관리자 확인 페이지: `/admin/conversions`
- 7일 보관 정책 기반 자동 삭제: `cleanup_old_records.py`
- Mac launchd 자동 실행 예시: `scripts/macos/*.plist`

## 금지사항

- `page.pdf()` 사용 금지
- `full_page=True`에만 의존 금지
- 기존 긴 1페이지 PDF 기능 깨뜨리기 금지
- `v3.0` 안정 기능보다 OCR 개선을 우선하지 말 것
- OCR/DOM 수정 시 PDF가 빈 페이지가 되면 즉시 중단
- 기능 깨짐 상태를 성공 처리하지 말 것

## 현재 해결 중인 문제

- Notion 상단 로그인/가입 배너 제거
- 일부 텍스트가 선택되지 않는 문제
- DOM 텍스트 레이어 누락 문제
- OCR/DOM 중복 삽입 시 복사 결과가 깨지는 문제
- Windows에서 Markdown 문서 한글 인코딩 깨짐 문제
- Mac mini 상시 실행 구조 구성
- 변환 내역 DB 저장 및 오래된 output 자동 삭제

## 테스트 명령

```bash
python -m py_compile app.py
python -m py_compile app.py db.py cleanup_old_records.py
python -m unittest discover -s tests
python tests/run_server_pdf_flow.py
python tests/run_db_cleanup_validation.py
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
Flask 서버 터미널과 `cloudflared` 터미널이 둘 다 켜져 있어야 한다.

launchd 자동 실행 예시는 다음 파일에 있다.

- `scripts/macos/com.notion_pdf.flask.plist`
- `scripts/macos/com.notion_pdf.cloudflare.quick.plist`
- `scripts/macos/com.notion_pdf.cleanup.plist`

quick tunnel은 임시 주소가 바뀔 수 있다. 고정 주소 운영은 named tunnel로 전환한다.

## DB 및 자동 삭제

- DB 파일: `instance/notion_pdf.db`
- DB 모듈: `db.py`
- cleanup 스크립트: `cleanup_old_records.py`
- cleanup 로그: `logs/cleanup.log`
- 기본 보관 기간: 7일

수동 cleanup:

```bash
python cleanup_old_records.py
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

검증:

```bash
python - <<'PY'
from pathlib import Path
for p in list(Path('docs').glob('*.md')) + [Path('README.md')]:
    text = p.read_text(encoding='utf-8')
    print('OK UTF-8:', p, len(text))
PY
```

## 기록 정책

- 어떤 AI CLI가 작업하든 `docs/작업로그.md`에 기록한다.
- 테스트 결과는 `docs/테스트결과.md`에 기록한다.
- 현재 상태 변경은 `docs/현재상태.md`에 기록한다.
- 새 세션 인수인계 내용은 `docs/AI작업인수인계.md`에 기록한다.
- 사용자 승인 전까지 git commit/push를 하지 않는다.
