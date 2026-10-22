# Security Audit & Vulnerability Assessment Report

**Project:** AI Novel-to-Webtoon Studio  
**Audit Date:** 2026-10-22  
**Auditor:** Antigravity Senior Application Security Reviewer  
**Classification:** Internal Technical Security Review  

---

## 1. Executive Summary

A comprehensive application security review was conducted across the backend API, service boundaries, storage layer, database models, background task runners, and AI prompt pipelines.

The audit verified strong existing defenses for:
- Input size limiting (10MB document upload limit, 20MB reference image limit with HTTP 413 responses).
- System tag prompt injection neutralization (`<system>`, ````system`).
- Server-side approval gate enforcement preventing AI self-approval and unapproved panel rendering.
- Path traversal sanitization in file name storage.

However, the audit confirmed **two critical/high-severity vulnerabilities** and several medium-severity hardening opportunities:
1. **SEC-01 (Critical): Broken Object-Level Authorization (BOLA/IDOR)** across all project resources.
2. **SEC-02 (High): Unauthenticated Storage Endpoint Serving Private Manuscripts**.
3. **SEC-03 (Medium): Silent Provider Fallback Masquerading as Configured AI**.
4. **SEC-04 (Medium): Default Permissive Export Approval Flag**.
5. **SEC-05 (Low): Unscoped Style Profile Query Across Multi-Tenant Projects**.

---

## 2. Detailed Findings & Vulnerability Matrix

### Finding SEC-01: Broken Object-Level Authorization (BOLA / IDOR)
- **Finding ID:** `SEC-01`
- **Severity:** **Critical**
- **Affected Component:** `backend/app/api/v1/projects.py`, `documents.py`, `references.py`, `analysis.py`, `planning.py`, `storyboard.py`, `generation.py`, `export.py`, `jobs.py`
- **Evidence:**
  In `projects.py:62-77`, `get_project` and `update_project` receive `user_id = Depends(get_current_user_id)` but query:
  ```python
  stmt = select(Project).where(Project.id == project_id)
  ```
  Neither the owner (`project.owner_id == user_id`) nor project membership (`ProjectMember`) is verified!
  Similarly, endpoints for manuscripts, references, storyboard panels, and jobs accept any `project_id` and execute mutations without checking if the calling user owns or has access to the project.
- **Realistic Impact:** Any user with valid credentials (or in multi-user deployments) can read, modify, delete, or generate illustrations on another creator's private story projects simply by knowing or guessing the project's UUID.
- **Reproduction Method:**
  1. User A creates a project (`User-A-Key`).
  2. User B (`User-B-Key`) calls `GET /api/v1/projects/{project_a_id}` or `POST /api/v1/projects/{project_a_id}/documents`.
  3. The request succeeds with HTTP 200/201 instead of being denied with HTTP 403 Forbidden.
- **Recommended Fix:** Implement a centralized authorization dependency `verify_project_access(project_id, user_id, db)` that asserts the user is either the project owner or an authorized member; raise HTTP 403 Forbidden otherwise. Enforce this dependency on all project-scoped routes.
- **Fix Status:** Identified -> Remediating in Phase 8.
- **Regression Test:** `backend/tests/test_13_security_authorizations.py::test_cross_user_project_access_blocked`.

---

### Finding SEC-02: Unauthenticated Storage Endpoint Serving Private Manuscripts
- **Finding ID:** `SEC-02`
- **Severity:** **High**
- **Affected Component:** `backend/app/api/v1/assets.py:9-30`
- **Evidence:**
  ```python
  @router.get("/storage/{category}/{filename}")
  async def serve_stored_file(category: str, filename: str):
      rel_key = f"{category}/{filename}"
      abs_path = storage_service.get_absolute_path(rel_key)
      ...
      return FileResponse(path=str(abs_path), media_type=media_type)
  ```
  This endpoint:
  1. Lacks any authentication check (`Depends(get_current_user_id)` is omitted).
  2. Does not restrict `category` to public media types (`assets`, `references`) versus private source text (`documents`).
  3. Does not verify whether the requesting user owns the underlying project or asset.
- **Realistic Impact:** An external attacker or unauthorized party can download unreleased story manuscripts and export ZIP archives from `/api/v1/storage/documents/{filename}` without providing credentials.
- **Reproduction Method:**
  Issue an unauthenticated `GET /api/v1/storage/documents/sample_novel.txt`. The server returns the full novel manuscript text.
- **Recommended Fix:**
  1. Add authentication to the storage route.
  2. Disallow direct public downloading of `documents` category; require manuscript access to go through authenticated `/api/v1/projects/{project_id}/documents` endpoints with project authorization.
  3. Validate `category` against an explicit whitelist `{"references", "assets", "exports"}` and sanitize path resolution with `pathlib.Path.is_relative_to`.
- **Fix Status:** Identified -> Remediating in Phase 8.
- **Regression Test:** `backend/tests/test_13_security_authorizations.py::test_unauthenticated_document_download_blocked`.

---

### Finding SEC-03: Silent Provider Fallback Masquerading as Configured AI
- **Finding ID:** `SEC-03`
- **Severity:** **Medium**
- **Affected Component:** `backend/app/providers/factory.py:9-34`
- **Evidence:**
  ```python
  if name == "openai":
      p = OpenAIProvider()
      if p.is_configured():
          return p
  return mock_llm_provider
  ```
- **Realistic Impact:** When a user or system administrator configures `LLM_PROVIDER=openai` or passes `provider_override="openai"`, but the API key is missing or invalid, the system silently returns mock procedural output while reporting success. The user believes they are evaluating a real model, concealing configuration errors and violating architectural honesty requirements.
- **Reproduction Method:** Set `LLM_PROVIDER=openai` without setting `OPENAI_API_KEY`. Call `provider_factory.get_llm_provider()`. It returns `MockLLMProvider` instead of raising an informative error.
- **Recommended Fix:** If an explicit provider other than `"mock"` is requested and is not configured, raise a `RuntimeError` or `HTTPException` detailing the missing configuration rather than silently falling back.
- **Fix Status:** Identified -> Remediating in Phase 8.
- **Regression Test:** `backend/tests/test_13_security_authorizations.py::test_unconfigured_provider_explicit_failure`.

---

### Finding SEC-04: Permissive Default for Export Approval Gate
- **Finding ID:** `SEC-04`
- **Severity:** **Medium**
- **Affected Component:** `backend/app/api/v1/export.py:17`, `backend/app/export/webtoon_exporter.py:80-87`
- **Evidence:**
  `export.py` endpoint signature:
  ```python
  async def trigger_episode_export(episode_id: str, require_all_approved: bool = Query(False)):
  ```
  And in `webtoon_exporter.py`:
  ```python
  if img is None:
      # Fallback: create placeholder panel
      img = Image.new("RGB", (800, 1000), ...)
  ```
- **Realistic Impact:** Default API calls allow unapproved episodes, incomplete storyboards, or missing illustrations to be packaged and exported as finished webtoons with synthetic placeholders.
- **Recommended Fix:** Change default parameter to `require_all_approved: bool = Query(True)`. In `webtoon_exporter.py`, raise an error if any panel or the episode is unapproved, or if asset files are missing, unless in an explicit draft export mode.
- **Fix Status:** Identified -> Remediating in Phase 8.
- **Regression Test:** `backend/tests/test_13_security_authorizations.py::test_unapproved_export_blocked_by_default`.

---

### Finding SEC-05: Unscoped Style Profile Query in Background Runner
- **Finding ID:** `SEC-05`
- **Severity:** **Low / Integrity**
- **Affected Component:** `backend/app/workers/job_runner.py:189-196`
- **Evidence:**
  ```python
  style_stmt = (
      select(StyleProfileVersion)
      .join(StyleProfileVersion.style_profile)
      .order_by(StyleProfileVersion.version_number.desc())
  )
  ```
  Does not filter by `StyleProfile.project_id == job.project_id`.
- **Realistic Impact:** If multiple projects exist in the database with differing art styles (e.g. Manga ink vs Watercolor fantasy), an episode generation job could inadvertently query and apply the style profile from another user's project.
- **Recommended Fix:** Add `.where(StyleProfile.project_id == job.project_id)` to the query.
- **Fix Status:** Identified -> Remediating in Phase 8.
- **Regression Test:** `backend/tests/test_13_security_authorizations.py::test_scoped_style_profile_lookup`.

---

## 3. Summary of Remediations Plan

| Finding | Severity | Proposed Fix |
|---|---|---|
| **SEC-01** | Critical | Enforce `verify_project_access` dependency across all project routes. Return HTTP 403 on ownership mismatch. |
| **SEC-02** | High | Restrict `/storage` categories to non-sensitive assets; disallow raw document retrieval; add path validation with `is_relative_to`. |
| **SEC-03** | Medium | Provider factory raises explicit error on unconfigured non-mock providers. |
| **SEC-04** | Medium | Default `require_all_approved=True` on export endpoint; raise `ValueError` on unapproved/missing assets. |
| **SEC-05** | Low | Filter style profile queries strictly by `project_id`. |
