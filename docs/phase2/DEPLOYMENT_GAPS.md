# Phase 2 — Database & Production Deployment Gaps Report
**Project:** AI Novel-to-Webtoon Studio  
**Date:** October 24, 2026  
**Auditor & DevOps Specialist:** Antigravity Senior Software Architect & Security Reviewer  
**Classification:** Production Infrastructure & Gap Analysis  

---

## 1. Executive Summary

This report assesses the persistence layer, migration framework, background worker durability, and production readiness of the **AI Novel-to-Webtoon Studio**.

The local SQLite database and async connection pooling are verified and operating cleanly. Genuine Alembic migrations have been initialized and verified with initial schema version `5d971c9c3a00_initial_schema.py`. However, PostgreSQL testing is documented as **BLOCKED** due to local environment constraints (no PostgreSQL service or Docker engine). 

Six critical production gaps—spanning distributed job queues, cloud blob storage, federated identity, API rate limiting, audit observability, and automated data retention—are itemized with concrete architectural remediation roadmaps.

---

## 2. Database & Migration Status

### 2.1 SQLite Local Persistence
- **Driver:** `aiosqlite` with SQLAlchemy 2.0 Asyncio engine.
- **Connection Configuration:** `sqlite+aiosqlite:///./storage/studio.db`
- **Verification:**
  - Database schema initialized via `Base.metadata.create_all` and validated via Alembic upgrade.
  - Async session lifecycles properly handled with `AsyncSessionLocal()` and scoped context managers.
  - Concurrency verified: `busy_timeout` handling and immediate failure of non-retryable validation errors prevents database locking.

### 2.2 Alembic Database Migrations
- **Status:** **CONFIGURED & VERIFIED**
- **Artifacts:**
  - `alembic.ini`: Configured with project settings.
  - `alembic/env.py`: Async migration runner connected to `backend.app.core.config.settings.DATABASE_URL` and `Base.metadata`.
  - Baseline Migration: `alembic/versions/5d971c9c3a00_initial_schema.py` generated and applied via `alembic upgrade head`.
  - Dependencies: Added `alembic>=1.13.0` to `backend/requirements.txt`.

### 2.3 PostgreSQL Compatibility Evaluation
- **ORM Schema Compatibility:**
  - Primary Keys: Models utilize `String(36)` with UUID generators, fully compatible with PostgreSQL `UUID` or `VARCHAR(36)`.
  - JSON Fields: Uses SQLAlchemy generic `JSON`, translating to native `JSONB` in PostgreSQL.
  - Timestamps: Uses timezone-aware UTC datetimes (`DateTime(timezone=True)`).
  - Relationships & Foreign Keys: Explicit cascade delete constraints defined across `projects -> documents`, `projects -> story_bibles`, `scenes -> beats -> panels -> dialogues`.
- **Live Verification Status:** **BLOCKED**
  - *Reason:* Neither Docker nor a local PostgreSQL service is installed on the host machine. The Python virtual environment does not contain `asyncpg` or `psycopg`.
  - *Instruction Compliance:* In accordance with Master Prompt instructions, PostgreSQL is **not** marked as verified until live CRUD and migration transactions are executed against an active PostgreSQL instance.

---

## 3. Background Job Worker & Idempotency

### 3.1 Worker Implementation
- **Current Architecture:** Async in-process worker queue backed by SQLite `jobs` table (`backend/app/workers/job_runner.py`).
- **Idempotency & Stale Job Recovery:**
  - On application startup, `recover_orphaned_jobs()` scans the database for jobs left in `running` state (caused by server crashes or abrupt restarts).
  - Jobs with `retry_count < max_retries` are reset to `queued` with incremented retry count.
  - Jobs exceeding maximum retries are transitioned to `failed` with descriptive error messages.
  - Verified in `test_05_job_recovery_preserves_approvals_and_data_integrity`: orphaned jobs are recovered without corrupting existing panel approvals, asset versions, or storyboard metadata.

---

## 4. Production Deployment Gaps

### Gap 1: Distributed Job Processing (Horizontal Worker Scaling)
- **Current State:** Jobs are scheduled via `asyncio.create_task()` in the web server process. If multiple API instances run behind a load balancer, workers cannot coordinate job locks, and restarting a pod interrupts all active tasks.
- **Production Requirement:**
  - Decouple API server from worker processes.
  - Introduce Celery with Redis/RabbitMQ, or Postgres-native queueing (e.g. `pg-boss` or `ARQ` with Redis).
  - Implement worker heartbeats, task timeouts, and dead-letter queues.

### Gap 2: Cloud Object Storage (S3 / Cloudflare R2 / GCS)
- **Current State:** Stored files (`references`, `assets`, `exports`, `documents`) are saved to local filesystem directory (`./storage/`).
- **Production Requirement:**
  - Multi-server deployments require distributed cloud blob storage.
  - Refactor `backend/app/services/storage.py` to support an S3-compatible backend (AWS S3, Cloudflare R2, Google Cloud Storage) with signed presigned URLs for large downloads.

### Gap 3: Federated Identity & Multi-Tenancy (OAuth2 / OIDC)
- **Current State:** Authentication uses `X-Studio-Auth` with HMAC token verification. Development mode allows test identifiers.
- **Production Requirement:**
  - Replace development header trust boundary with standard JWT Bearer tokens issued by an identity provider (Auth0, Clerk, Cognito, or Keycloak).
  - Enforce tenant organization boundaries with workspace role-based access control (Admin, Creator, Reviewer).

### Gap 4: Rate Limiting & Compute Cost Throttling
- **Current State:** No rate limiting on generation or export endpoints.
- **Production Requirement:**
  - Hosted AI providers (OpenAI, Stability, Gemini) incur direct API costs. Malicious or runaway users could rack up thousands of dollars in DALL-E 3 or SD3 calls.
  - Implement Redis-backed token bucket rate limiting on `/generation-jobs` and `/export-jobs` (e.g., maximum 20 draft generations per hour per user).

### Gap 5: Structured Observability, Tracing & Audit Logging
- **Current State:** Basic standard library logging to console.
- **Production Requirement:**
  - Integrate OpenTelemetry distributed tracing across API requests, database queries, and async AI provider calls.
  - Structured JSON logging sent to Datadog, Grafana Loki, or AWS CloudWatch.
  - Immutable audit trail recording creator approvals, prompt modifications, and export downloads.

### Gap 6: Data Retention & Automated Cleanup Policies
- **Current State:** All generated drafts, edit versions, and export zip files are kept indefinitely on disk.
- **Production Requirement:**
  - Establish automated lifecycle policies:
    - Retain approved final artwork permanently.
    - Delete rejected or stale draft thumbnails after 30 days.
    - Clean up temporary sliced export ZIPs after 7 days.
    - Implement GDPR/CCPA user data deletion cascades.
