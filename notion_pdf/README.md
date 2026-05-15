# 📄 Notion → 페이지 분할 없는 PDF 변환기

Notion 페이지를 한 장으로 이어지는 PDF로 변환해주는 로컬 웹 앱이에요.

---

## 🚀 설치 및 실행

### 1. 필요 패키지 설치

```bash
pip install flask playwright beautifulsoup4 requests
python -m playwright install chromium
```

### 2. 서버 실행

```bash
cd notion_pdf
python app.py
```

### 3. 브라우저에서 열기

```
http://localhost:5000
```

---

## 📌 사용법

### URL 입력 방식
1. Notion 페이지를 **웹에 게시(Public)** 상태로 설정
   - Notion 페이지 → 우측 상단 `공유` → `웹에 게시` 켜기
2. URL을 입력하고 변환 시작

### 파일 업로드 방식
1. Notion에서 **HTML로 내보내기**
   - 페이지 우측 상단 `···` → `내보내기` → `HTML` 선택
2. 다운로드된 `.html` 파일을 업로드

---

## ⚙️ 변환 옵션

| 옵션 | 설명 |
|------|------|
| 용지 너비 | A4(794px), A3(1123px), Letter(816px), 넓게(1200px) |
| 여백 | 없음 ~ 넓게 선택 가능 |

---

## 🛠 작동 원리

- **Playwright(Chromium)** 를 사용해 페이지를 실제 브라우저로 렌더링
- 페이지의 실제 전체 높이를 측정해서 `@page { size: Wpx Hpx }` 로 설정
- `page-break` 관련 CSS를 모두 비활성화해서 끊김 없는 PDF 생성

---

## 📋 요구사항

- Python 3.8+
- 인터넷 연결 (URL 방식 사용 시)
