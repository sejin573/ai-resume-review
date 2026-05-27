# ai 이력서 첨삭

Korean AI resume and cover letter review service MVP with a safe training-data pipeline.

This project includes:
- FastAPI backend
- React + Vite frontend
- review history
- multi-step AI review pipeline
- consent-based training sample collection
- approved-source ingestion
- anonymization and curation
- curated JSONL export for future SFT / LoRA / QLoRA work

## Safety and licensing

We do **not** scrape copyrighted resume or cover-letter sites without permission.

Blocked by default:
- Saramin
- JobKorea
- LinkedIn
- Ringker
- blogs
- cafes
- any other third-party site without explicit permission

Allowed sources:
1. user-consented submissions from our own service
2. admin-uploaded CSV / JSONL with confirmed usage rights
3. partner datasets with documented permission
4. public datasets with AI-training-compatible licenses
5. manually created seed data

Rules:
- raw personal data must not be exported to the fine-tuning dataset
- imported raw text is only for controlled admin review
- anonymization is required before curation/export
- export is blocked if high-risk PII remains

## Repository structure

```text
ai 이력서 첨삭/
  backend/
  frontend/
  data/
    seed/
    test_imports/
  exports/
```

## Backend setup

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Example `.env`:

```env
APP_NAME=ai 이력서 첨삭
APP_ENV=development
SECRET_KEY=replace-with-a-long-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./local.db
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
MOCK_AI_MODE=true
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
ADMIN_EMAILS=["test@example.com"]
```

## Database schema / migration

Primary schema setup:

```powershell
cd backend
psql -U postgres -d ai_resume_review -f init_schema.sql
```

Ingestion pipeline migration:

```powershell
cd F:\장세진\미니 프로젝트\자소서\project
psql -U postgres -d ai_resume_review -f backend\migrations\20260520_ingestion_pipeline.sql
```

For local SQLite development, the app also runs `create_all()` and bootstrap upgrades on startup.

## Run backend

```powershell
cd backend
uvicorn app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## Run frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

## Core API

- `POST /auth/signup`
- `POST /auth/login`
- `POST /reviews`
- `GET /reviews`
- `GET /reviews/{id}`
- `POST /reviews/{id}/refine`
- `POST /reviews/{id}/feedback`
- `POST /reviews/{id}/consent-training`

Admin endpoints:
- `POST /admin/data-sources`
- `GET /admin/data-sources`
- `PATCH /admin/data-sources/{id}`
- `POST /admin/import/csv`
- `POST /admin/import/jsonl`
- `POST /admin/import/approved-urls`
- `GET /admin/imported-documents`
- `GET /admin/imported-documents/{id}`
- `POST /admin/imported-documents/{id}/anonymize`
- `POST /admin/imported-documents/{id}/reject`
- `POST /admin/imported-documents/{id}/create-training-sample`
- `GET /admin/training-samples`
- `GET /admin/training-samples/{id}`
- `POST /admin/training-samples/{id}/review`
- `POST /admin/export-training-jsonl`
- `POST /admin/export/curated-training-jsonl`

## Review workflow notes

- `cover_letter_text` is required and must be at least 20 characters.
- `resume_text`, `target_job_role`, and `job_posting_text` are optional. When they are empty, the review runs from the cover letter and general role context.
- The AI review returns `sentence_reviews` for sentence-by-sentence coaching. Each reviewed sentence is marked as `good`, `okay`, `needs_fix`, or `risky`.
- Good sentences show why they work. Sentences that need work can be clicked in the document and replaced with the suggested rewrite.
- Suggested rewrites must be actual cover-letter sentences, not editing instructions. The service filters out instruction-like text such as "add this" or "make it more specific".
- Rewrites should use facts from the original draft, such as technologies, projects, tools, and responsibilities already mentioned. The AI must not invent companies, awards, certifications, project names, or performance numbers.
- Missing numbers may remain as placeholders like `[성과 수치]`, `[기간]`, or `[횟수]`, but a rewrite should not be mostly placeholders.
- If a suggested rewrite looks unsafe to apply directly, the UI marks it as direct-edit recommended and hides the apply action.
- The legacy `suggestions` field is still returned for compatibility and as a fallback when sentence reviews are not available.
- Each sentence review and suggestion is anchored to source text; the frontend uses `start_index` / `end_index` first and falls back to the closest matching original sentence.
- Applying a sentence rewrite updates the current working draft. It does not silently persist a submitted final document.
- To use the working draft as the submitted version, save it through the final document panel or the current-draft final-save action.
- PDF export is generated from the saved final document when one exists. The UI saves the current final candidate immediately before export to avoid exporting stale text.
- Users should review every suggested rewrite before final submission; sentence-level suggestions are coaching aids, not guaranteed final copy.

## Packaging and Git hygiene

Do not include local runtime, dependency, or secret files in Git commits or deployment ZIPs:

- `.env`, `*.env`, `backend/.env`, `frontend/.env`
- `frontend/node_modules/`
- `frontend/dist/`
- `backend/.venv/`, `backend/.venv_py314_backup/`
- `.tools/`
- `backend/local.db`, `backend/test.db`, `*.db`
- `exports/`
- `__pycache__/`, `.pytest_cache/`
- `*.zip`, `*.log`

## Training-data pipeline

### Source registry

`data_sources`

- source types:
  - `user_consent`
  - `admin_upload`
  - `partner_dataset`
  - `public_dataset`
  - `manual_seed`
  - `approved_url_list`
- license statuses:
  - `unknown`
  - `approved`
  - `rejected`
  - `needs_review`

Ingestion is allowed only when `license_status=approved`.

### Imported documents

`imported_documents` can temporarily store raw text for admin review.

Important:
- raw text is never exported directly to fine-tuning JSONL
- production should encrypt this field or move it to secure object storage

### Anonymization

`backend/app/services/anonymization_service.py`

Masks:
- names
- emails
- phone numbers
- birth dates
- resident-registration-like patterns
- addresses
- school names
- company names
- URLs
- account numbers
- student / employee IDs

Placeholders:
- `[NAME]`
- `[EMAIL]`
- `[PHONE]`
- `[BIRTH_DATE]`
- `[RRN]`
- `[ADDRESS]`
- `[SCHOOL]`
- `[COMPANY]`
- `[URL]`
- `[ACCOUNT]`
- `[ID]`

### Curation rules

Samples are exportable only when all of these are true:
- data source is approved
- `quality_status=reviewed`
- `reviewed_by_human=true`
- PII risk is below the threshold
- assistant message contains valid review JSON
- required review schema fields exist

## Seed dataset generator

The seed generator creates fully fictional, privacy-safe, license-safe samples for pipeline testing.

It does **not**:
- scrape external sites
- use real accepted cover letters
- use real personal data

Command:

```powershell
python backend/scripts/generate_seed_training_data.py --count-per-role 50
```

Output:

```text
data/seed/generated_seed_samples.jsonl
```

Generated seed data defaults:
- `data_source=manual_seed`
- `quality_status=draft`

## Seed dataset import into shared pipeline

Import the generated seed JSONL into the same curation/export pipeline used by other training samples:

```powershell
python backend/scripts/import_seed_training_data.py
```

This script:
- creates or reuses the `Fictional Manual Seed Dataset` data source
- validates every JSONL line
- validates assistant JSON
- validates review schema
- rejects PII
- skips duplicate `original_cover_letter` values
- stores samples in `anonymized_training_samples`

## Admin curation workflow

Real production curation must happen through the admin UI, not through the local bulk-review helper.

Recommended flow:
1. Generate seed data
2. Import seed data
3. Open the admin training sample list
4. Inspect a training sample detail page
5. Mark the sample reviewed or rejected
6. Export curated JSONL
7. Use the exported JSONL later for LoRA / QLoRA training preparation

Admin frontend routes:
- `/admin/training-samples`
- `/admin/training-samples/:id`
- `/admin/training-export`

## Local-only bulk review helper

For local pipeline testing only:

```powershell
python backend/scripts/mark_seed_samples_reviewed.py
```

Rules:
- only works when `APP_ENV` is `local` or `development`
- marks manual-seed samples as reviewed
- sets `reviewed_by_human=true`
- adds the note:
  `Bulk reviewed for local pipeline testing. Must not be used for production evaluation without human review.`

This helper is only for local export verification. Production usage still requires real human review.

## User-facing workflow

1. Open the landing page
2. Sign up or log in
3. Create a new review in the workspace
4. Review AI feedback, score cards, and before/after comparison
5. Review sentence-level improvement suggestions and apply them selectively
6. Refine the improved text with preset or custom instructions
7. Copy, save, or export the final text
8. View saved history later from the review history page

## AI review pipeline

CoverFit AI now uses a versioned review pipeline instead of a single opaque prompt.

Prompt versions:
- `REVIEW_PROMPT_VERSION=coverfit-review-v2`
- `REFINE_PROMPT_VERSION=coverfit-refine-v2`
- `REVIEW_PIPELINE_VERSION=coverfit-pipeline-v2`

Review steps:
1. Job posting analysis
2. Cover letter diagnosis
3. Final structured review generation
4. JSON validation and repair

Job posting analysis extracts:
- `job_keywords`
- `required_competencies`
- `preferred_experiences`
- `tone_hint`
- `risk_notes`

Diagnosis extracts:
- `core_experiences`
- `weak_points`
- `missing_evidence`
- `overused_expressions`
- `job_fit_notes`
- `recommended_structure`

Final review response remains frontend-compatible and still includes:
- `total_score`
- `scores`
- `summary`
- `problems`
- `improvement_strategy`
- `improved_cover_letter`
- `interview_questions`
- `missing_keywords`
- `strengths`

Optional metadata-style fields may also be present:
- `job_keywords`
- `rewritten_structure`
- `evidence_suggestions`
- `ats_keyword_notes`
- `final_review_checklist`

## Scoring rubric

Each category is scored `0-100`.

- `job_fit`: 직무 적합도
- `specificity`: 경험의 구체성
- `achievement`: 성과/수치 표현
- `writing_quality`: 문장력
- `uniqueness`: 차별성
- `structure`: 논리 구조
- `keyword_match`: 채용공고 키워드 반영

Conservative scoring rules:
- vague cover letters should usually stay below `65`
- good but generic cover letters usually fall in `65-78`
- strong role-aligned cover letters can reach `79-90`
- `90+` should be rare and require exceptional evidence
- when job posting detail is weak, `keyword_match` stays conservative
- when action/result evidence is missing, `achievement` stays low
- when the text is too short, `specificity` and `structure` should stay low
- when wording is exaggerated, `writing_quality` and `uniqueness` should be adjusted down

## Review modes

- `quick`: concise summary, top problems, shorter improved draft
- `detailed`: balanced full review
- `strict`: more critical scoring and sharper diagnosis
- `rewrite-focused`: puts more emphasis on the final improved draft

The API accepts `rewrite-focused`. For compatibility, internal normalization also accepts `rewrite_focused`.

## Refinement behavior

`POST /reviews/{id}/refine`

Refinement is now versioned and follows stricter rules:
- preserve the user's real experience
- do not invent achievements, certificates, company names, or numbers
- use placeholders like `[기간]`, `[성과 수치]`, `[횟수]` when proof is missing
- return:
  - `refined_text`
  - `change_summary`
  - `warnings`

Preset refinement intent:
- `더 구체적으로`
- `성과 중심으로`
- `자연스럽게`
- `신입답게`
- `700자로 줄이기`
- `면접에서 설명하기 쉽게`
- `과장 줄이기`

## Quality feedback API

Users can now rate review helpfulness for future quality analysis:

- `POST /reviews/{id}/feedback`

Request:

```json
{
  "rating": "helpful",
  "reason": "개선 방향이 구체적이어서 수정에 도움이 됐습니다."
}
```

Allowed ratings:
- `helpful`
- `not_helpful`

This feedback is stored separately from training export for now.

## Important review safety rule

The review and refinement pipeline must not invent user achievements.

That means:
- no fake company names
- no fake certificates
- no fake numbers
- no fake durations
- no fake promotions or roles

If evidence is missing, the improved text should keep the experience truthful and use placeholders or explicit improvement guidance instead.

## 문장별 보완 제안

CoverFit AI now returns sentence-level suggestions together with the main review result.

What it does:
- marks weak or high-impact sentences from the original cover letter
- explains why they need improvement
- proposes a safer rewrite that preserves the user's real experience
- lets the user apply suggestions one by one in the editor

Suggestion rules:
- only 3 to 7 high-impact suggestions are returned
- suggestions focus on vague expression, weak job relevance, missing action/result, unsupported achievement, cliché phrases, tone, paragraph flow, and missing keywords
- missing numbers are expressed with placeholders such as `[기간]`, `[성과 수치]`, `[횟수]`, `[규모]`, `[도구]`
- the user remains in control and should review the final text before submission

Frontend behavior:
- `/reviews/new` shows:
  - `첨삭 표시 보기` preview with highlighted weak text
  - `문장별 보완 제안` cards
  - one-click apply
  - skip
  - undo last apply
- `/reviews/{id}` shows saved suggestions again and allows applying them into the current improved/final text flow

User-facing frontend routes:
- `/`
- `/dashboard`
- `/reviews/new`
- `/reviews/:id`
- `/reviews/history`
- `/templates`

## Product UI overview

The frontend is now organized as a document-centered SaaS workspace under the `CoverFit AI` product name.

Main user experience:
1. Public landing page
2. Dashboard for saved documents and score overview
3. New review workspace with:
   - left editor panel
   - right AI coach panel
   - review-mode toolbar
   - before/after editing flow
4. Saved review detail page with refinement history
5. Review history as a document library
6. Admin curation pages for training samples

Design direction:
- light workspace background
- white cards
- sticky panels
- Korean-friendly typography
- polished SaaS shell with sidebar and topbar

## Redesigned frontend routes

Public:
- `/`
- `/login`
- `/signup`

User app:
- `/dashboard`
- `/reviews/new`
- `/reviews/history`
- `/reviews/:id`
- `/templates`

Admin:
- `/admin/training-samples`
- `/admin/training-samples/:id`
- `/admin/training-export`

## Validation script

```powershell
python backend/scripts/validate_ingested_training_data.py
```

It checks:
- training sample validity
- counts by job role
- counts by source type
- PII signals
- duplicate texts
- assistant JSON validity
- export readiness

## Review quality evaluation script

```powershell
cd backend
.venv\Scripts\python.exe scripts\evaluate_review_quality.py
```

Behavior:
- when `OPENAI_API_KEY` exists, it can evaluate with the live OpenAI review pipeline
- when no API key exists, it runs schema/mock validation only

It writes a timestamped evaluation artifact to:

```text
backend/evaluation_outputs/review_quality_eval_YYYYMMDD_HHMMSS.json
```

## CSV / JSONL import formats

CSV:

```csv
document_type,job_role,original_title,original_text,source_reference,license_note
accepted_cover_letter,웹개발자 신입,샘플 제목,자기소개서 원문...,seed-1,internal rights confirmed
```

JSONL:

```json
{
  "document_type": "accepted_cover_letter",
  "job_role": "웹개발자 신입",
  "original_title": "샘플 제목",
  "original_text": "자기소개서 원문...",
  "source_reference": "partner-set-01",
  "license_note": "usage rights confirmed"
}
```

Sample fake import file:

```text
data/test_imports/accepted_cover_letters_sample.jsonl
```

## Approved URL import warning

`approved_url_list` import must only be used for sources with explicit permission.

The importer:
- fetches only the exact URLs provided
- does not crawl recursively
- tries to respect `robots.txt`
- does not bypass login, paywalls, captcha, rate limits, or anti-bot protection

## Tests

Run backend tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
```

Recommended local verification flow:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe scripts\evaluate_review_quality.py
.venv\Scripts\python.exe scripts\generate_seed_training_data.py --count-per-role 50
.venv\Scripts\python.exe scripts\import_seed_training_data.py
.venv\Scripts\python.exe scripts\mark_seed_samples_reviewed.py
.venv\Scripts\python.exe scripts\validate_ingested_training_data.py
```

Frontend commands:

```powershell
cd frontend
npm run build
npm run dev
```

There is currently no `npm run lint` script configured in `frontend/package.json`.

## Screenshots

Placeholder sections for future screenshots:
- landing page
- new review workspace
- saved review detail
- admin training sample curation

## Manual QA checklist

- public landing page loads when logged out
- logged-in user is redirected to `/dashboard`
- new review workspace loads at `/reviews/new`
- AI result appears in the right coach panel after analysis
- improved text can be copied
- improved text can be applied back into the editor
- refinement works from the refine tab
- history opens saved review detail
- admin pages still work
- mobile layout remains usable

Frontend automated tests are not configured yet. For now, use `npm run build` plus manual QA through the routes above.

## Current seed pipeline status

After importing the generated seed dataset and marking it reviewed for local testing:
- imported seed samples: `250`
- export-ready seed samples: `250`

One older user-consent sample remains non-exportable until a human review is recorded.

## Final document and PDF export workflow

The user-facing workflow is now clearer and less file-cabinet oriented:

1. Write or paste a cover letter draft.
2. Run AI review against the target role, resume summary, and job posting.
3. Apply the improved draft or refinement result.
4. Edit the final version manually in the `완성본 만들기` panel.
5. Save the final version.
6. Export the saved final version as PDF.

Backend endpoints:

```text
GET /reviews/{id}/final-document
PUT /reviews/{id}/final-document
GET /reviews/{id}/export/pdf
```

The PDF export includes:
- final cover letter text
- target job role
- review mode
- AI review summary
- score table
- strengths
- improvement points
- interview questions

The PDF generator uses ReportLab with built-in Korean CID fonts, so the project does not ship font files.

## Deployment guide

### Recommended MVP deployment

For the first public beta, use a split deployment:

```text
Frontend: Vercel
Backend API: Render Web Service
Database: Render Postgres or Supabase Postgres
AI: OpenAI API key through backend environment variables
```

### Frontend deployment on Vercel

1. Push the project to GitHub.
2. Create a new Vercel project.
3. Set the root directory to `frontend`.
4. Build command:

```bash
npm run build
```

5. Output directory:

```text
dist
```

6. Add environment variable:

```text
VITE_API_BASE_URL=https://your-backend-domain.onrender.com
```

`frontend/vercel.json` is included so React Router routes such as `/reviews/new` and `/reviews/:id` refresh correctly.

### Backend deployment on Render

Create a Render Web Service from the GitHub repository.

Recommended settings:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: ./start.sh
```

Required environment variables:

```text
APP_NAME=CoverFit AI
APP_ENV=production
SECRET_KEY=<long-random-secret>
DATABASE_URL=<postgres connection string>
OPENAI_API_KEY=<your-openai-api-key>
OPENAI_MODEL=gpt-4o-mini
MOCK_AI_MODE=false
CORS_ORIGINS=["https://your-frontend-domain.vercel.app"]
ADMIN_EMAILS=["your-admin-email@example.com"]
```

The backend normalizes `postgres://` and `postgresql://` into the `postgresql+psycopg://` SQLAlchemy driver format automatically.

### Database

Use PostgreSQL for production. SQLite is fine for local testing only.

The FastAPI app currently creates and updates required schema on startup. For a larger production service, replace this with Alembic migrations before scaling.

### Production checklist before launch

- Replace `SECRET_KEY` with a long random value.
- Set `CORS_ORIGINS` to the exact frontend domain only.
- Confirm `MOCK_AI_MODE=false` and `OPENAI_API_KEY` is set.
- Use PostgreSQL, not SQLite.
- Add a privacy policy and terms page.
- Add account deletion and training-data deletion request handling.
- Add rate limits and daily free usage limits.
- Hide admin routes based on role, not just navigation.
- Add error monitoring and basic access logs.
- Back up the production database.
- Confirm PDF export works with Korean text on the production server.

## Optional inputs and inline suggestions

CoverFit AI now supports a lighter review flow:

- `cover_letter_text` is required
- `target_job_role` is optional
- `resume_text` is optional
- `job_posting_text` is optional

This means users can submit:

- cover letter only
- cover letter + target job role
- cover letter + any combination of resume summary and job posting

When resume summary or job posting is missing, the review still runs and the AI responds conservatively:

- keyword matching is evaluated more carefully when no job posting is provided
- role alignment is phrased more generally when the target role is missing
- evidence validation is limited to the cover letter when no resume summary is provided

### 문장별 보완 제안

The review workspace includes inline sentence-level suggestions.

- weak sentences or short paragraphs are highlighted inside `첨삭 표시`
- clicking a highlighted phrase opens a small proofreading note near the text
- users can apply one suggestion at a time with `이 문장 적용`
- suggestions preserve the user’s actual experience
- when facts are missing, placeholders such as `[기간]`, `[성과 수치]`, `[횟수]` can appear instead of invented details
- users should always review the final text before submission

### Local validation commands

Backend:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest
```

Frontend:

```powershell
cd frontend
npm run build
```
