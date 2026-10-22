# Deployment Readiness & Database Portability Audit

**Project:** AI Novel-to-Webtoon Studio  
**Audit Date:** 2026-10-22  
**Auditor:** Antigravity Senior Software Architect & Database Engineer  

---

## 1. Executive Summary

This audit assesses the technical readiness of the application stack to transition from local single-node development (SQLite + local filesystem) to a scalable production deployment (PostgreSQL + S3 object storage + standalone distributed workers).

### Current Assessment: **Development Prototype Ready — Production Blockers Identified**

---

## 2. Database Portability Audit (SQLite to PostgreSQL)

| Area | Current Implementation | PostgreSQL Migration Path | Risk Level |
|---|---|---|---|
| **Primary Keys & UUIDs** | `String(36)` with `uuid.uuid4().hex` defaults | PostgreSQL native `UUID` or `String(36)`. Compatible without schema rewriting. | Low |
| **JSON Serialization** | `sa.JSON` column types across all models (`world_rules`, `payload`, `manifest_data`, etc.) | Fully supported in SQLAlchemy 2.0. Maps to `jsonb` in PostgreSQL and `TEXT` in SQLite. | Low |
| **Foreign Keys & Cascades** | Explicit `ForeignKey` constraints with `ondelete="CASCADE"` on child tables. | SQLite requires `PRAGMA foreign_keys = ON;` (currently enabled via engine event). PostgreSQL enforces foreign keys natively. | Low |
| **Timestamps & Timezones** | Python `datetime.datetime.utcnow()` used in model defaults. | **Deprecated in Python 3.12+**. Must be updated to `datetime.now(datetime.timezone.utc)` to avoid timezone skew when migrating to PostgreSQL `TIMESTAMP WITH TIME ZONE`. | **Medium (Fixed in Phase 8)** |
| **Async Session Lifecycle** | `get_db` FastAPI dependency yielding `AsyncSession` with commit/rollback handlers. | Compatible with `asyncpg` driver (`postgresql+asyncpg://...`). | Low |
| **Database Migrations** | Initial schema created dynamically via `Base.metadata.create_all`. | Production deployments require an Alembic migration environment to track schema revisions without destructive table recreation. | **High (Required for Scale)** |

---

## 3. Worker Architecture & Concurrency Audit

1. **In-Process vs Distributed Worker:**
   - The current worker `backend/app/workers/job_runner.py` runs inside the web server process via `asyncio.create_task`.
   - **Local Development Assessment:** Ideal for lightweight, single-box developer environments and automated test suites.
   - **Production Bottleneck:** In multi-worker Uvicorn configurations (`uvicorn --workers 4`), in-process `asyncio.create_task` leads to duplicate jobs and uncoordinated poll loops.
   - **Production Requirement:** Migrate to a dedicated task queue (Celery, ARQ, or Redis Queue) with independent worker containers.
2. **Crash & Restart Recovery:**
   - The `JobRunner.recover_orphaned_jobs()` method runs during FastAPI application startup (`lifespan`), inspecting the database for jobs stuck in `running` status and returning them to `queued` with an incremented retry count.
   - Tested and verified in `test_09_job_recovery_after_restart`.

---

## 4. Object Storage Portability

- **Current Implementation:** `LocalStorageService` at `storage/` (`documents`, `references`, `assets`, `exports`).
- **Path Sanitization:** `validate_safe_filename` and `get_safe_storage_path` prevent directory traversal.
- **Production Migration:** Implement an S3-compatible adapter (`boto3` / `aioboto3` or MinIO) matching the `StorageService` interface (`save_bytes`, `read_bytes`, `get_absolute_path` -> pre-signed URLs).

---

## 5. Security & Configuration Audit

1. **Environment Variables:**
   - `SECRET_KEY`: Defaults to a development fallback string. Production startup must assert `SECRET_KEY != "change-this-in-production-to-a-secure-random-key"`.
   - `DEBUG`: Must be set to `False` in production to prevent stack trace leakage.
2. **CORS:**
   - Defaults to `http://localhost:3000,http://127.0.0.1:3000`. Configurable via `ALLOWED_ORIGINS` environment variable.

---

## 6. Deployment Readiness Checklist

- [x] Python virtual environment isolated and dependencies pinned in `requirements.txt`.
- [x] Database tables create cleanly with SQLite async driver.
- [x] Foreign key integrity and relationship eager loading (`selectinload`) verified.
- [x] Restart recovery for interrupted jobs implemented.
- [x] Next.js 14 production build succeeds with 0 errors.
- [x] Static pages pre-rendered and bundle size optimized.
- [ ] Alembic migrations initialized for production schema change tracking.
- [ ] S3 object storage adapter implemented for stateless container deployments.
- [ ] Standalone Celery/Redis worker detached from HTTP server process.
- [ ] Production JWT authentication service configured to replace development API key header.
