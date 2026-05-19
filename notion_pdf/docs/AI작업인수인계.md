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
- 현재 테이블명: `conversions`
- `conversion_history` 테이블은 현재 없음
- 업로드 원본 파일 저장 위치: `uploads/YYYY-MM/`
- 변환 PDF 저장 위치: `output/pdf/`
- 변환 PNG 저장 위치: `output/png/`
- 추출 TXT 저장 위치: `output/txt/`
- 디버그 파일 위치: `output/debug/`
- 테스트 산출물 위치: `output/tests/`
- DB 주요 파일 경로 필드: `input_file_path`, `output_pdf_path`, `output_txt_path`, `output_png_path`
- cleanup 스크립트: `cleanup_old_records.py`
- cleanup 로그: `logs/cleanup.log`
- 기본 보관 기간: 7일

수동 cleanup:

```bash
python cleanup_old_records.py
```

## 2026-05-18 운영 기능 검증 메모

- 관리자 페이지: `/admin/conversions`
- 관리자 페이지 HTTP 확인 결과: 200
- 최근 기록: success/failed 모두 DB에 저장됨
- DB `output_pdf_path`는 실제 PDF 파일과 연결됨
- 일반 변환 결과 PDF/TXT는 현재 `output/` 폴더가 아니라 OS 임시 폴더의 `notion_pdf` 디렉터리에 저장됨
- `/output/<파일명>.pdf` 직접 접근 라우트는 없음, HTTP 404
- `/download/<job_id>`는 메모리 기반이라 서버 재시작 후 이전 job 다운로드 불가
- cleanup dry-run 및 실제 실행 통과
- launchd plist 문법 통과
- `start_flask.sh`는 테스트 포트에서 직접 실행 확인
- `start_cloudflare_quick_tunnel.sh`는 실행 권한과 `cloudflared` 경로만 확인, 실제 tunnel 연결은 이번 검증에서 실행하지 않음

다음 AI 작업자는 기능을 고치기 전에 아래 결정을 사용자에게 확인하는 것이 좋다.

1. 테이블명을 `conversions`로 유지할지 `conversion_history`로 변경할지
2. 변환 산출물을 `output/`에 저장할지 현재 임시 폴더 구조를 유지할지
3. `/output/<파일명>` 라우트를 만들 경우 인증 또는 만료 토큰을 적용할지
4. `/admin/conversions` 인증을 우선 추가할지

## 2026-05-19 output/uploads 구조 개선 메모

- HTML 업로드 원본은 `uploads/YYYY-MM/`에 저장된다.
- 변환 결과 PDF는 `output/pdf/`에 저장된다.
- 변환 결과 PNG는 `output/png/`에 저장된다.
- 변환 결과 TXT는 `output/txt/`에 저장된다.
- 디버그 PNG는 `output/debug/`에 저장된다.
- 검증 산출물은 `output/tests/`에 정리한다.
- 파일명은 `secure_filename`, timestamp, 원본 이름, 8자리 job id를 사용한다.
- 현재 파일명 규칙은 `YYYYMMDD_HHMMSS_원본이름_작업ID.ext`이다.
- 관리자 페이지 `/admin/conversions`에서 원본/PDF/TXT/PNG 다운로드 링크를 제공한다.
- 다운로드 라우트는 `/admin/conversions/<id>/download/<kind>` 형식이다.
- `<kind>`는 `input`, `pdf`, `txt`, `png`만 허용한다.
- 다운로드 대상은 DB에 저장된 경로이며, `uploads/` 또는 `output/` 하위 파일만 허용한다.
- cleanup은 만료된 DB 기록의 원본/PDF/TXT/PNG 파일을 함께 삭제한다.
- cleanup은 `uploads/`와 `output/` 하위 폴더를 재귀적으로 확인한다.
- 인증은 아직 없으므로 외부 공개 전 관리자 인증 추가가 필요하다.

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
