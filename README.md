# AI 이력서 첨삭

AI 기반 이력서 및 자기소개서 첨삭 서비스입니다.  
사용자가 작성한 자기소개서를 분석해 문장 개선안, 강점/약점, 누락 키워드, 예상 면접 질문, 최종 수정본을 제공하는 것을 목표로 합니다.

백엔드는 `FastAPI`, 프론트엔드는 `React + Vite`로 구성되어 있으며, 사용자 동의 기반의 학습 데이터 수집과 개인정보 비식별화 흐름까지 고려해 만든 프로젝트입니다.

> **개발 상태**: 개발 진행 중  
> **개발 기간**: 2026.05 ~ 현재  
> 현재 프로젝트는 서비스 아이디어를 실제 웹앱 형태로 구현한 MVP 단계이며, 기능 보강과 UI 개선, 첨삭 품질 고도화를 계속 진행 중입니다.

## 주요 기능

- 회원가입 / 로그인
- 이력서 및 자기소개서 첨삭 요청
- AI 기반 문항별 피드백 생성
- 문장 단위 개선 제안
- 강점, 문제점, 누락 키워드 분석
- 예상 면접 질문 생성
- 첨삭 결과 이력 관리
- 관리자용 학습 샘플 검수
- 개인정보 비식별화 후 학습 데이터 JSONL export
- 승인된 데이터 소스만 사용하는 안전한 학습 데이터 파이프라인

## 기술 스택

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT 인증
- SQLite / PostgreSQL 호환 구조
- OpenAI API 연동 구조
- Pytest 기반 테스트

### Frontend

- React
- Vite
- React Router
- CSS 기반 커스텀 UI

## 프로젝트 구조

```text
AI 이력서 첨삭/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      prompts/
    migrations/
    scripts/
    tests/
    init_schema.sql
    requirements.txt
  frontend/
    public/
    src/
      api/
      components/
      pages/
      styles/
      utils/
    package.json
  data/
    test_imports/
```

## 실행 방법

### 1. Backend 실행

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

Backend 기본 주소:

```text
http://127.0.0.1:8000
```

API 문서:

```text
http://127.0.0.1:8000/docs
```

### 2. Frontend 실행

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Frontend 기본 주소:

```text
http://127.0.0.1:5173
```

## 환경 변수 예시

실제 `.env` 파일은 Git에 올리지 않습니다.  
아래 값은 예시이며, 실제 키와 비밀번호는 각자 로컬 환경에만 설정해야 합니다.

```env
APP_NAME=AI 이력서 첨삭
APP_ENV=development
SECRET_KEY=<long-random-secret>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./local.db
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o-mini
MOCK_AI_MODE=true
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
ADMIN_EMAILS=["test@example.com"]
```

## 주요 API

- `POST /auth/signup`  
  회원가입

- `POST /auth/login`  
  로그인 및 토큰 발급

- `POST /reviews`  
  자기소개서 첨삭 요청

- `GET /reviews`  
  첨삭 이력 조회

- `GET /reviews/{review_id}`  
  첨삭 상세 조회

- `POST /admin/training-samples/import`  
  관리자 학습 데이터 import

- `POST /admin/training-samples/export`  
  비식별화된 학습 데이터 export

## 학습 데이터 정책

이 프로젝트는 무단 크롤링 데이터를 학습에 사용하지 않는 것을 원칙으로 합니다.

허용하는 데이터:

- 서비스 이용자가 학습 활용에 동의한 제출 데이터
- 관리자가 권한을 확인한 CSV / JSONL 데이터
- 사용 허가가 명확한 파트너 데이터
- AI 학습 사용이 허용된 공개 데이터셋
- 직접 작성한 seed 데이터

차단하는 데이터:

- 허가 없이 수집한 채용 사이트 자기소개서
- 블로그, 카페, 커뮤니티의 무단 수집 글
- 개인정보가 포함된 원문 데이터
- 저작권 또는 이용 약관이 불명확한 데이터

학습 데이터 export 전에는 개인정보 비식별화와 위험 문구 검사를 수행하도록 구성했습니다.

## 테스트

### Backend 테스트

```powershell
python -m pytest backend\tests -q
```

현재 확인된 결과:

```text
43 passed
```

### Frontend 테스트

```powershell
cd frontend
npm run test:suggestions
```

## 보안 관리

다음 파일과 폴더는 Git에 올리지 않습니다.

- `.env`
- 로컬 DB 파일
- 로그 파일
- `node_modules`
- Python 가상환경
- 빌드 결과물
- export 결과물

민감정보는 `.env.example`에는 예시 형태로만 남기고, 실제 값은 로컬 `.env`에서만 관리합니다.

## 프로젝트 목적

이 프로젝트는 단순한 AI 호출 데모가 아니라, 실제 서비스 운영을 고려한 이력서 첨삭 웹서비스 MVP입니다.

중점적으로 구현한 부분:

- 사용자 입력 기반 첨삭 흐름
- 결과 저장 및 이력 관리
- 관리자 검수 기반 학습 데이터 관리
- 개인정보 비식별화
- 안전한 데이터 export
- 백엔드 테스트 코드
- 프론트엔드 페이지 및 컴포넌트 구조화

향후에는 첨삭 품질 평가 자동화, 문항별 합격 가능성 분석, 기업/직무별 맞춤 피드백, PDF export, 배포 환경 분리 등을 추가할 수 있습니다.

## 개발 과정

이 프로젝트는 2026년 5월부터 개발을 시작했으며, 현재도 기능 보강과 첨삭 품질 개선을 진행 중입니다. 자기소개서를 작성하는 사용자가 더 빠르게 초안을 점검하고, 실제 제출 가능한 문장으로 다듬을 수 있도록 만드는 것을 목표로 시작했습니다. 단순히 AI 응답을 화면에 보여주는 수준이 아니라, 회원 관리, 첨삭 이력, 관리자 검수, 학습 데이터 관리까지 포함하는 서비스형 MVP로 확장했습니다.

현재는 완성된 상용 서비스라기보다, 실제 서비스 구조를 갖춘 개발 진행 중 프로젝트로 보고 있습니다. 앞으로 첨삭 품질 평가, 직무별 피드백 정교화, 배포 환경 분리 등을 계속 개선할 계획입니다.

주요 개발 흐름은 다음과 같습니다.

1. **서비스 기획과 MVP 구조 설계**
   - 이력서/자기소개서 첨삭이라는 문제를 중심으로 사용자 흐름을 정리했습니다.
   - 입력, 분석, 피드백, 개선문, 저장, 다시 보기로 이어지는 기본 사용 흐름을 설계했습니다.
   - 백엔드는 FastAPI, 프론트엔드는 React + Vite 구조로 분리했습니다.

2. **백엔드 API 구현**
   - 회원가입, 로그인, JWT 인증, 첨삭 요청, 첨삭 이력 조회 API를 구현했습니다.
   - SQLAlchemy 모델과 Pydantic 스키마를 분리해 데이터 저장 구조와 API 응답 구조를 정리했습니다.
   - OpenAI API를 연결할 수 있는 구조를 만들고, API Key가 없을 때도 개발 가능한 mock 모드를 준비했습니다.

3. **AI 첨삭 파이프라인 구성**
   - 자기소개서 본문, 지원 직무, 이력서 요약, 채용공고 정보를 바탕으로 첨삭 결과를 생성하도록 구성했습니다.
   - 전체 점수, 항목별 점수, 강점, 문제점, 누락 키워드, 개선 전략, 예상 면접 질문을 나눠서 응답하도록 설계했습니다.
   - 문장별 보완 제안을 통해 사용자가 특정 문장을 직접 고쳐볼 수 있도록 했습니다.

4. **프론트엔드 화면 구현**
   - 랜딩 페이지, 로그인/회원가입, 대시보드, 새 첨삭 작성, 첨삭 결과 상세, 이력 페이지를 만들었습니다.
   - 점수 카드, 피드백 카드, 문장별 제안, 개선문 패널, 복사 버튼 등 반복 사용되는 UI를 컴포넌트로 분리했습니다.
   - 단순 입력 폼이 아니라 실제 서비스처럼 사용할 수 있는 작업 공간 형태로 화면을 구성했습니다.

5. **관리자와 학습 데이터 관리**
   - 사용자 동의 데이터와 관리자 업로드 데이터를 구분해 관리할 수 있도록 했습니다.
   - 무단 크롤링을 사용하지 않는 정책을 README와 코드 구조에 반영했습니다.
   - 개인정보 비식별화, 학습 샘플 검수, JSONL export 흐름을 추가했습니다.

6. **테스트와 품질 검증**
   - API, 서비스 로직, 리뷰 파서, 학습 데이터 파이프라인에 대한 pytest 테스트를 작성했습니다.
   - 현재 백엔드 테스트 기준 `43 passed` 상태를 확인했습니다.
   - 실제 `.env`, 로컬 DB, 로그, 가상환경, 빌드 결과물은 Git에 올라가지 않도록 정리했습니다.

7. **GitHub 업로드와 문서화**
   - 로컬 `project` 폴더를 `AI 이력서 첨삭` 프로젝트로 정리했습니다.
   - GitHub CLI를 설치하고 `sejin573/ai-resume-review` 저장소를 생성해 업로드했습니다.
   - README를 한글 중심으로 다시 정리해 포트폴리오 제출용으로 보기 쉽게 다듬었습니다.

## Codex 활용

이 프로젝트는 OpenAI Codex를 활용해 개발했습니다.

Codex는 아이디어를 바로 코드로 옮기는 바이브 코딩 도구이면서, 동시에 구조 점검과 테스트 보강을 도와주는 페어 프로그래밍 도구로 사용했습니다.

활용한 부분은 다음과 같습니다.

- FastAPI 백엔드 구조 설계
- React 컴포넌트 분리와 페이지 구성
- AI 첨삭 응답 구조 설계
- 개인정보 비식별화 및 학습 데이터 정책 정리
- 테스트 코드 작성과 오류 검수
- GitHub 업로드 준비
- README와 포트폴리오용 설명 문서 정리

전체 개발 방향, 기능 우선순위, 자기소개서 서비스라는 문제 정의는 사용자가 결정했고, Codex는 구현 속도를 높이고 코드 품질을 점검하는 보조 도구로 활용했습니다. 이를 통해 짧은 시간 안에 백엔드, 프론트엔드, 테스트, 문서화까지 포함한 MVP 형태로 프로젝트를 완성할 수 있었습니다.
