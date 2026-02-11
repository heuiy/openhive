# Shipping Mark PDF 생성기 (웹앱)

LG Chem Life Sciences 제조혁신팀 - 부스틴 Shipping Mark 출력용 웹 애플리케이션

## 지원 국가 프로필

| 프로필 | 주요 기능 | 페이지 방향 |
|--------|-----------|-------------|
| 아프간 | 표준 주소 오버레이 | Portrait |
| 오만 | Consignee 변경 (HUZAIFA) | Landscape |
| 우즈벡 | 표준 주소 오버레이 | Portrait |
| 칠레 | 등록번호 + 제품명 변경 | Landscape |
| 멕시코 | 표준 주소 오버레이 | Portrait |
| 브라질 외 | 표준 주소 오버레이 (좌표 상이) | Portrait |
| 브라질 | QR코드 + 배치번호 + Consignee/제품명/박스텍스트 변경 | Portrait |

## 설치 및 실행

### 1. uv 설치 (최초 1회)

```powershell
# PowerShell 에서 실행
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 프로젝트 폴더 이동

```powershell
cd "D:\#.Secure Work Folder\Shipping Mark\shipping-mark-webapp"
```

### 3. 가상환경 생성 및 의존성 설치

```powershell
uv sync
```

### 4. 실행

```powershell
uv run app.py
```

브라우저에서 **http://127.0.0.1:5000** 접속

## 폴더 구조

```
shipping-mark-webapp/
├── app.py              # Flask 웹앱 (메인)
├── pyproject.toml      # uv 프로젝트 설정
├── templates/
│   └── index.html      # 웹 UI
├── pdf/                # ★ PDF 원본 파일을 여기에 넣으세요
│   └── (WMS에서 출력한 .pdf 파일들)
├── pic/
│   └── boostin.png     # 브라질용 QR코드 이미지 (직접 배치)
└── README.md
```

## 사용 방법

### 기본 흐름

1. **pdf/ 폴더에 PDF 원본 배치** — WMS에서 출력한 PDF를 `pdf/` 폴더에 넣습니다
2. **국가 프로필 선택** — 국가에 따라 PDF 처리 방식이 자동 설정됩니다
3. **전체 박스 수 입력** — 전체 출력할 박스 수량
4. **국가별 추가 설정** — 고정 주소, consignee, 제품명 등 (프로필에 따라 자동 표시)
5. **배치 설정** — 드롭다운에서 PDF 선택 + 복사 매수 (여러 배치 추가 가능)
6. **미리보기** — 첫 페이지를 미리 확인
7. **최종 PDF 생성** — 모든 배치를 합본한 PDF 다운로드

> **참고**: pdf/ 폴더에 새 파일을 추가한 뒤에는 "PDF 목록 새로고침" 버튼을 클릭하세요.
> 파일 업로드 팝업 없이 서버 폴더에서 직접 읽어옵니다.

### 좌표 미세 조정

- "고급 설정" 섹션을 열면 모든 오버레이 요소의 X, Y 좌표를 수정할 수 있습니다
- PDF 좌표계: **좌측 하단이 (0, 0)**, X는 오른쪽, Y는 위쪽으로 증가
- 프린터 환경이 바뀌면 여기서 좌표를 조정하면 됩니다 (재배포 불필요)

### 1페이지 vs 2페이지 PDF 처리 규칙

기존 cmd 스크립트와 동일한 로직:
- **1페이지 PDF**: 복사 매수만큼 첫 페이지 반복
- **2페이지 PDF**: (복사 매수 - 1)만큼 첫 페이지 반복 + 마지막에 2페이지 추가

### 브라질 프로필 사용 시

1. `pic/boostin.png` 파일을 앱 폴더의 `pic/` 디렉토리에 넣어주세요
2. 배치별로 "배치 번호" 입력란이 나타납니다
3. QR코드 크기/위치는 고급 설정에서 조정 가능합니다

## 기존 cmd 스크립트와의 차이

| 항목 | 기존 (cmd) | 웹앱 |
|------|-----------|------|
| 실행 방식 | cmd에서 대화식 입력 | 웹 브라우저 |
| 좌표 조정 | 코드 수정 후 재실행 | 웹 UI에서 즉시 변경 |
| 미리보기 | 불가 | 첫 페이지 미리보기 |
| PDF 파일 선택 | 고정 폴더에서 번호 입력 | `pdf/` 폴더 드롭다운 선택 (업로드 불필요) |
| 다중 배치 | 순차 대화식 | 한 화면에서 일괄 설정 |
