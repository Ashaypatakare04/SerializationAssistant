# Baseline Audit & Verification Report
**Project:** AI Novel-to-Webtoon Studio  
**Date of Baseline Run:** 2026-10-22  
**Auditor:** Antigravity Senior Software Architect & Security Reviewer  
**Repository State:** Clean working tree at commit `0bd87b9` (plus added ESLint configuration)

---

## 1. Repository Inventory

### Backend (`backend/`)
- **Framework:** FastAPI 0.110.0, Python 3.13 / Pydantic V2, Uvicorn, SQLAlchemy 2.0 (Asyncio)
- **Local Database:** SQLite with `aiosqlite` at `storage/studio.db` (test database: `storage/test_studio.db`)
- **Virtual Environment:** `backend/venv/` (Python 3.13)
- **Service Layer:**
  - `source_ingestion.py`: Manuscript parsing, chapter/section locator extraction, prompt injection sanitizer.
  - `story_analysis.py`: LLM-driven story bible creation (premise, characters, events, continuity facts).
  - `style_analysis.py`: Visual style profile extraction and versioning.
  - `serialization.py`: Arc and episode adaptation planning.
  - `storyboard.py`: Webtoon panel generation and beat progression.
  - `approval.py`: Multi-stage human approval gates (rejection of automated/AI self-approval).
  - `versioning.py`: Dependency graph and stale job overwrite guards.
  - `storage.py`: Local filesystem object store with path traversal sanitation.
- **Workers:** `backend/app/workers/job_runner.py` (persistent async queue in SQLite with orphaned job recovery on startup).
- **QA Modules:** `backend/app/qa/` (Narrative QA, Visual QA, Sequence QA).
- **Exporter:** `backend/app/export/webtoon_exporter.py` (Pillow-based long vertical strip stitcher, slicer [max 8000px], dialogue rasterizer, ZIP manifest builder).
- **Providers:**
  - `mock_provider.py`: Procedural, deterministic Pillow visual graphics engine and heuristic story extractor.
  - `openai_provider.py`: Adapter for GPT-4o and DALL-E 3 (unconfigured in baseline).
  - `gemini_provider.py`: Adapter for Google Gemini 1.5 Pro / Flash (unconfigured in baseline).
  - `stability_provider.py`: Adapter for Stable Diffusion 3 / Core (unconfigured in baseline).
  - `factory.py`: Provider resolution factory.

### Frontend (`frontend/`)
- **Framework:** Next.js 14.2.15 (App Router), React 18.3.1, TypeScript 5, Tailwind CSS 3.4.14
- **Components:**
  - `Navbar.tsx`: Stage navigation, QA Modal launcher, Provider Capabilities viewer.
  - `ProjectDashboard.tsx`: Project list, creation modal, 1-click Demo Pilot seeder.
  - `SourceWorkspace.tsx`: Manuscript intake, section viewer, editable Story Bible tabs.
  - `ReferenceStyleWorkspace.tsx`: Reference image manager with role assignment, Style Profile viewer.
  - `SerializationWorkspace.tsx`: Episode adaptation planning.
  - `StoryboardEditor.tsx`: Panel layout editor, beat details, aspect ratio, camera angles.
  - `IllustrationReview.tsx`: Prompt manifest viewer, draft/final generation trigger, approval gate buttons.
  - `WebtoonReader.tsx`: Vertical scrolling reader with dialogue overlay preview and ZIP exporter.
  - `QAReportModal.tsx`: Visual, Narrative, and Sequence QA inspector.
  - `CapabilitiesModal.tsx`: System AI provider inspector and cost estimation.

### Storage & Artifacts (`storage/`)
- `storage/documents/`: Ingested manuscript files.
- `storage/references/`: Uploaded reference images.
- `storage/assets/`: Generated draft and final panel artwork.
- `storage/exports/`: Compiled webtoon ZIP packages.

---

## 2. Environment Details

- **Operating System:** Windows 11 (64-bit)
- **Python Version:** Python 3.13.0
- **Node.js Version:** Node.js v20+ with npm
- **Database Engine:** SQLite (aiosqlite async driver)
- **Active Environment Variables:** Default development settings from `.env.example` (`APP_ENV=development`, `LLM_PROVIDER=mock`, `IMAGE_PROVIDER=mock`)

---

## 3. Baseline Commands Executed & Results

| # | Check / Command | Exit Code | Result | Warnings / Failure Details |
|---|-----------------|-----------|--------|----------------------------|
| 1 | `backend\venv\Scripts\pytest backend\tests -v` | **0** | **12 / 12 Passed** in 6.53s | **647 Warnings** (Pydantic V2 `Config` deprecation; `datetime.utcnow()` deprecation). |
| 2 | `npx tsc --noEmit` (in `frontend/`) | **0** | **0 Errors** | TypeScript compilation clean. |
| 3 | `npm run lint` (in `frontend/`) | **0** | **Passed** | 5 `react-hooks/exhaustive-deps` warnings (`page.tsx`, `IllustrationReview.tsx`, `QAReportModal.tsx`, `WebtoonReader.tsx`). ESLint installed and configured. |
| 4 | `npm run build` (in `frontend/`) | **0** | **Build Successful** | Static page generation (4/4 routes) succeeded. Bundle size 109 kB First Load JS. |
| 5 | `Invoke-RestMethod http://127.0.0.1:8000/health` | **0** | **HTTP 200 OK** | `{status: "healthy", app: "AI Novel-to-Webtoon Studio", env: "development"}` |
| 6 | `Invoke-WebRequest http://localhost:3000` | **0** | **HTTP 200 OK** | Next.js development server serving home dashboard correctly. |

---

## 4. Initial Baseline Discrepancies & Issues Identified

1. **Broken Object-Level Authorization (BOLA/IDOR)**:
   - `get_current_user_id` returns `"creator_default_user"` in development mode.
   - However, endpoints across `projects.py`, `documents.py`, `references.py`, `analysis.py`, `planning.py`, `storyboard.py`, `generation.py`, `export.py`, and `jobs.py` fail to verify that the requesting `user_id` is actually the project owner or authorized member before allowing read or write operations.
2. **Missing Reference Passing in Background Generation**:
   - In `backend/app/workers/job_runner.py` (lines 219, 226), `character_refs` was hardcoded to `[]` when calling `img_provider.generate_draft` and `img_provider.generate_final`. Primary character references uploaded by the creator were not propagated to the generator.
3. **Unscoped Style Profile Lookup**:
   - In `backend/app/workers/job_runner.py` (line 189), the style profile version query did not filter by `project_id`, meaning the runner could pick up an arbitrary style profile from a different project in multi-project databases.
4. **Silent Fallback to Mock Provider**:
   - In `backend/app/providers/factory.py`, if a real provider (`openai`, `gemini`, `stability`) is requested but not configured, the factory silently returned the mock provider without raising an error or notifying the caller, violating the non-negotiable honesty requirement.
5. **Permissive Export Defaults & Asset Fallback**:
   - In `backend/app/api/v1/export.py`, `require_all_approved` defaulted to `False` (`Query(False)`), allowing unapproved panels to be exported by default.
   - In `backend/app/export/webtoon_exporter.py`, missing panel assets generated placeholder panels rather than halting export and enforcing approval.
6. **Public Serving of Stored Documents**:
   - `GET /api/v1/storage/{category}/{filename}` in `assets.py` served files without authentication or authorization, allowing anyone to download private novel manuscripts if filename is known or enumerated.
7. **647 Deprecation Warnings**:
   - Models and schemas use deprecated Pydantic v1 `Config` classes and deprecated `datetime.utcnow()`.
8. **Frontend Hook Dependency Warnings**:
   - 5 React hooks in frontend components miss dependencies in `useEffect` arrays.

---

## 5. Uncommitted Changes to Preserve
- No prior user changes were found uncommitted. Working tree was clean at `0bd87b9`. Added `.eslintrc.json` to enable reproducible linting.
