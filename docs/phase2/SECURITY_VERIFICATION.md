# Phase 2 — Security & Boundary Verification Report
**Project:** AI Novel-to-Webtoon Studio  
**Date:** October 24, 2026  
**Auditor & Lead Security Reviewer:** Antigravity Senior Software Architect & Security Reviewer  
**Classification:** Internal Technical Security Audit  

---

## 1. Executive Summary

A comprehensive application security review was executed to validate identity boundaries, broken object-level authorization (BOLA/IDOR), static asset isolation, path traversal guards, upload validation, and production fail-closed policies across the API and storage layers.

All identified vulnerabilities from the Phase 1 audit and new findings in Phase 2 have been remediated with minimal, surgically verified changes. The security posture is formally protected by automated regression test suites in `test_11_12_security_provider.py`, `test_13_security_and_remediations.py`, and `test_14_phase2_validation.py`.

---

## 2. Security Findings & Boundary Analysis

### 2.1 Identity Mechanism & Production Trust Boundary (`X-Studio-Auth`)
- **Vulnerability Identified:**
  In the baseline implementation, `get_current_user_id` accepted any string supplied in the `X-Studio-Auth` header and returned it as the authenticated user ID. In development mode, this provided convenience for local testing and multi-user simulations. However, in production mode, this would allow untrusted callers to spoof arbitrary user identities (e.g. `X-Studio-Auth: victim_user_id` or `admin`).
- **Remediation Applied:**
  1. **Strict Environment Boundary:**
     - In `APP_ENV in ("development", "test")`: Plain-text identifiers or signed tokens in `X-Studio-Auth` are accepted for test convenience, defaulting to `"creator_default_user"` if absent.
     - In `APP_ENV == "production"`: Plain-text string identity assertion is strictly prohibited. Requests require a cryptographically verified HMAC-SHA256 signed bearer token (`create_access_token` / `verify_token`).
  2. **Production Fail-Closed Guard:**
     - In production mode, if `settings.SECRET_KEY` is missing or remains set to the default insecure development string (`"dev-secret-key-studio-insecure-only-for-local"`), the API immediately fails closed with HTTP `500 Internal Server Error: Production misconfiguration: SECRET_KEY must be securely configured`.
     - In production mode, requests without a valid signed token are rejected with HTTP `401 Unauthorized`.
- **Verification Evidence:**
  Asserted in `test_01_production_identity_fails_closed_when_unconfigured` in `test_14_phase2_validation.py`.

---

### 2.2 Static Storage Router & Cross-User Asset Isolation
- **Vulnerability Identified:**
  The static file retrieval endpoint `GET /api/v1/storage/{category}/{filename}` previously allowed direct unauthenticated access to `references`, `assets`, and `exports`. While novel manuscripts (`documents`) were blocked in Phase 1, any unauthenticated or unauthorized third party who guessed or enumerated filenames could download private creator reference sheets, proprietary panel artwork, or complete webtoon zip archives.
- **Remediation Applied:**
  1. Bound `serve_stored_file` to `user_id = Depends(get_current_user_id)` and database session `db = Depends(get_db)`.
  2. Resolved the parent `project_id` associated with the stored file:
     - For `references`: Queries `ReferenceAsset.project_id` matching `storage_key`.
     - For `assets`: Joins `AssetVersion` to `Asset` to retrieve `Asset.project_id`.
     - For `exports`: Queries `Export.project_id` matching `storage_key`.
  3. Enforced project ownership via `await verify_project_access(project_id, user_id, db)`. If the requesting user does not own or have collaborator access to the project, the system raises HTTP `403 Forbidden`.
  4. Blocked raw manuscript retrieval (`"documents"`) with HTTP `403 Forbidden`.
- **Verification Evidence:**
  Asserted in `test_02_static_storage_cross_user_isolation` in `test_14_phase2_validation.py`.

---

### 2.3 Broken Object-Level Authorization (BOLA / IDOR)
- **Vulnerability Identified:**
  Multiple API endpoints accepted UUIDs for projects, storyboards, panels, and documents without verifying that the authenticated user was the owner or an authorized collaborator.
- **Remediation Applied:**
  Protected all endpoints via `verify_project_access(project_id, user_id, db)` across:
  - `projects.py`, `documents.py`, `references.py`, `analysis.py`, `planning.py`, `storyboard.py`, `generation.py`, `export.py`, and `jobs.py`.
- **Verification Evidence:**
  Asserted in `test_01_cross_user_project_access_blocked` in `test_13_security_and_remediations.py`.

---

### 2.4 Path Traversal & Filename Sanitization
- **Vulnerability Identified:**
  Upload and storage endpoints handling filename inputs risk directory traversal escapes (e.g., `../../etc/passwd` or `..\..\Windows\System32`).
- **Remediation Applied:**
  1. `validate_safe_filename(filename: str)`: Strips path separators, enforces regex `[^a-zA-Z0-9_\-\.]` substitution, and prefixes hidden/dotfiles with `safe_`.
  2. `get_safe_storage_path(base_dir: str, rel_path: str)`: Enforces `target_path.resolve().relative_to(base.resolve())`. If the resolved path escapes the base directory, raises HTTP `400 Bad Request: Illegal path traversal detected`.
- **Verification Evidence:**
  Asserted in `test_11_security_and_safe_boundaries` in `test_11_12_security_provider.py`.

---

### 2.5 File Upload Validation & Malformed Payload Rejection
- **Controls Enforced:**
  1. **Maximum File Size Enforcement:** Uploads exceeding 25MB are rejected with HTTP `413 Request Entity Too Large`.
  2. **Allowed File Extensions:** Manuscripts restricted to `.txt`, `.md`. References restricted to `.png`, `.jpg`, `.jpeg`.
  3. **Magic Byte / Pillow Format Validation:** Image uploads are opened with `PIL.Image.open()` to verify genuine image headers before storage. Corrupted or executable files disguised as images are rejected with HTTP `400 Bad Request`.

---

## 3. Authorization Matrix

| Endpoint Group | Method | Target Resource | Required Authorization | Enforcement Mechanism |
|---|---|---|---|---|
| `/projects` | `POST`, `GET` | User projects | Authenticated User | Filtered by `owner_id == user_id` |
| `/projects/{id}` | `GET`, `PATCH` | Project details | Project Owner / Member | `verify_project_access` (403 on IDOR) |
| `/projects/{id}/documents` | `POST`, `GET` | Novel manuscripts | Project Owner / Member | `verify_project_access` |
| `/projects/{id}/references` | `POST`, `GET` | Visual references | Project Owner / Member | `verify_project_access` |
| `/projects/{id}/story-bible` | `GET`, `PATCH` | Story Canon & Bible | Project Owner / Member | `verify_project_access` |
| `/panels/{id}` | `PATCH` | Storyboard panel | Panel Project Owner | Resolved to project -> `verify_project_access` |
| `/panels/{id}/generation-jobs` | `POST` | Art generation | Panel Project Owner | Resolved to project -> `verify_project_access` |
| `/artifacts/{id}/approvals` | `POST` | Approval sign-off | Human Creator (Owner) | Human sign-off required (no AI self-approval) |
| `/episodes/{id}/export-jobs` | `POST` | Webtoon export | Episode Project Owner | Requires 100% panel approval by default |
| `/exports/{id}/download` | `GET` | Production ZIP | Export Project Owner | `verify_project_access` |
| `/storage/references/*` | `GET` | Reference images | Asset Project Owner | Project lookup -> `verify_project_access` |
| `/storage/assets/*` | `GET` | Panel artwork | Asset Project Owner | Project lookup -> `verify_project_access` |
| `/storage/exports/*` | `GET` | Exported ZIP | Export Project Owner | Project lookup -> `verify_project_access` |
| `/storage/documents/*` | `GET` | Raw manuscript | **FORBIDDEN** | Category blocked (HTTP 403) |
