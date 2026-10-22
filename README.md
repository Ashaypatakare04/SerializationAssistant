# AI Novel-to-Webtoon Studio

> **Creator-Controlled AI Studio Transforming Original Literary Works into Art-Directed Vertical Webtoons.**

Built for creators, visual artists, and novelists. This studio adapts an original novel, short story, or manuscript into a vertically scrolling webtoon format (manhwa style). It enforces reference-faithful visual styles, canonical character identity consistency, source narrative fidelity, beat-level emotional direction, and explicit human creator approval gates.

---

## 1. Core Principles

- **Human Creative Control**: AI performs bounded creative suggestions; only the human creator approves stories, styles, storyboards, and final illustrations. Automated AI self-approval is strictly forbidden.
- **Visual Style Fidelity**: Extracts versioned linework, anatomy, facial construction, shading, background treatment, and color relationships from creator reference images.
- **Reference Isolation**: Style is extracted without borrowing external characters, dialogue, or foreign story events.
- **Character Consistency**: Canonical character records track hair cut/color, wardrobe, distinctive features, and proportions across all sequential panels.
- **Emotional Pacing Without Style Drift**: Pacing progresses dynamically from comedy to serious tension at the beat level while global rendering aesthetics remain stable.
- **Safe Revisions & Stale Protection**: Revising a panel specification resets approval and prevents stale background generation jobs from overwriting newer approved assets.
- **Export Integrity**: Stitches panels into continuous vertical reading strips (slicing at standard mobile heights) and packages individual panels, slices, and `manifest.json` into a production ZIP.

---

## 2. Technology Stack

- **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS, Lucide Icons.
- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0 (Async), Pydantic V2, Pillow.
- **Persistence**: SQLite (Local Async) with clean PostgreSQL migration path; local object storage adapter.
- **Background Worker**: Database-backed durable job runner with restart recovery and stale overwrite guards.
- **AI Integration**: Hybrid provider layer supporting hosted APIs (OpenAI, Gemini, Stability), local diffusion endpoints, and a deterministic offline Mock Provider (Pillow procedural synthesizer).

---

## 3. Quickstart & Setup

### Prerequisites
- Python 3.11+ (Tested on Python 3.13)
- Node.js 18+ (Tested on Node v22.21.0)
- Git

### Step 1: Clone & Configure Environment
```bash
git clone https://github.com/your-org/SerializationAssistant.git
cd SerializationAssistant

# Copy environment template
cp .env.example .env
```
*(Leave credentials blank in `.env` to run in zero-cost offline mock mode)*

### Step 2: Backend Setup
```bash
# Set up Python virtual environment
python -m venv backend/venv

# Activate venv (Windows PowerShell)
.\backend\venv\Scripts\Activate.ps1
# (On macOS/Linux: source backend/venv/bin/activate)

# Install dependencies
pip install -r backend/requirements.txt
```

### Step 3: Frontend Setup
```bash
cd frontend
npm install
cd ..
```

---

## 4. Running the Application Locally

### Start Backend (Port 8000)
```bash
.\backend\venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: `http://127.0.0.1:8000/docs`

### Start Frontend (Port 3000)
```bash
cd frontend
npm run dev
```
Open your browser to: `http://localhost:3000`

> **1-Click Pilot Demo**: On the studio dashboard, click **"Load Demo Pilot"** to automatically initialize the full 8-panel *"Shadows in the Rain"* mystery webtoon pilot with characters, references, style profile, and storyboard!

---

## 5. Running Automated Acceptance & Security Tests

The test suite validates all 17 non-negotiable acceptance, security, and remediation tests with **zero warnings**:

```bash
# Run complete backend test suite (17 passed in ~10s)
.\backend\venv\Scripts\pytest backend\tests -v

# Run visual benchmark harness
.\backend\venv\Scripts\python scripts\visual_benchmark.py

# Run frontend lint and production build verification
cd frontend
npm run lint
npm run build
cd ..
```

### Test Coverage Summary (17/17 Passed)
- **Test 1**: Story fidelity & character preservation with source locators (`test_01_story_fidelity.py`).
- **Test 2**: Reference isolation: style extracted without narrative borrowing (`test_02_reference_isolation.py`).
- **Test 3**: Style profile versioning & attribute modifications (`test_03_04_style_character.py`).
- **Test 4**: Canonical character appearance consistency across panels (`test_03_04_style_character.py`).
- **Test 5**: Beat-level emotional direction changes without visual drift (`test_05_emotional_transitions.py`).
- **Test 6**: Approval gate enforcement: blocks final generation until approved (`test_06_approval_gate_enforcement.py`).
- **Test 7**: Targeted revision safety: modifying one panel preserves others (`test_07_08_revision_stale.py`).
- **Test 8**: Stale background job overwrite guard (`test_07_08_revision_stale.py`).
- **Test 9**: Server restart job recovery from running state (`test_09_10_recovery_export.py`).
- **Test 10**: Vertical webtoon slice stitching, manifest, and ZIP export (`test_09_10_recovery_export.py`).
- **Test 11**: Security checks: path traversal rejection, upload file size limits (`test_11_12_security_provider.py`).
- **Test 12**: Real provider capability detection and transparent mock reporting (`test_11_12_security_provider.py`).
- **Test 13**: Cross-user Broken Object-Level Authorization (BOLA/IDOR) protection (`test_13_security_and_remediations.py`).
- **Test 14**: Static asset category whitelisting & private document blocking (`test_13_security_and_remediations.py`).
- **Test 15**: Honest provider configuration: unconfigured real providers fail loudly (`test_13_security_and_remediations.py`).
- **Test 16**: Strict export approval gates: unapproved panels rejected by default (`test_13_security_and_remediations.py`).
- **Test 17**: Character reference and dependency propagation in generation worker (`test_13_security_and_remediations.py`).

---

## 6. Security & Multi-Tenancy Architecture

The platform enforces zero-trust boundaries across storage and compute:
- **Object-Level Authorization (BOLA/IDOR)**: Every endpoint validates ownership via `verify_project_access`, preventing cross-user inspection or manipulation of projects, storyboards, and assets.
- **Private Document Isolation**: Raw novel manuscripts uploaded to `storage/documents/` are strictly inaccessible via the static file router. Only whitelisted public visual assets (`references`, `assets`, `exports`) can be rendered.
- **Path Traversal Protection**: File paths are validated using Python's `target_path.resolve().relative_to(base.resolve())` to prevent directory traversal escapes.
- **AI Provider Transparency**: Silent fallback from cloud providers (OpenAI, Gemini, Stability) to mock generation is eliminated. Non-configured providers raise explicit `RuntimeError`s.

---

## 7. Visual Benchmark Suite

Run the automated visual benchmark evaluation suite across three core narrative test cases:
```bash
python scripts/visual_benchmark.py
```
- **TC-01-ESTABLISHING-SHOT**: Evaluates background complexity, lighting, and environmental atmosphere.
- **TC-02-CHARACTER-INTRODUCTION**: Evaluates anatomy, linework, and costume consistency.
- **TC-03-EMOTIONAL-CLIMAX**: Evaluates dramatic lighting, expressions, and framing.
Benchmark results and metadata are written to `storage/benchmarks/benchmark_summary.json`.

---

## 8. API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/projects` | `POST` / `GET` | Create and list serialization projects |
| `/api/v1/projects/{id}/documents` | `POST` / `GET` | Upload manuscripts (.txt, .md) and view parsed sections |
| `/api/v1/projects/{id}/references` | `POST` / `GET` | Upload reference images and assign roles |
| `/api/v1/projects/{id}/analysis-jobs` | `POST` | Trigger Story Bible extraction |
| `/api/v1/projects/{id}/story-bible` | `GET` / `PATCH` | Inspect and edit canonical Story Bible and characters |
| `/api/v1/projects/{id}/style-analysis-jobs` | `POST` | Trigger visual style analysis |
| `/api/v1/projects/{id}/style-profile` | `GET` / `PATCH` | Inspect and edit versioned visual style profile |
| `/api/v1/projects/{id}/adaptation-plans` | `POST` / `GET` | Propose and view serialization plans |
| `/api/v1/episodes/{id}/storyboard-jobs` | `POST` | Generate sequential storyboard panels |
| `/api/v1/panels/{id}` | `PATCH` | Edit camera framing, actions, dialogue, or emotion |
| `/api/v1/artifacts/{id}/approvals` | `POST` | Human creator signs explicit approval |
| `/api/v1/panels/{id}/generation-jobs` | `POST` | Generate draft or final artwork (enforces approval gate) |
| `/api/v1/assets/{id}/edit-jobs` | `POST` | Targeted localized correction / inpainting |
| `/api/v1/episodes/{id}/qa-report` | `GET` | Comprehensive Narrative, Visual, and Sequence QA audit |
| `/api/v1/episodes/{id}/export-jobs` | `POST` | Compile vertical webtoon slices and export ZIP (default: requires all approved) |
| `/api/v1/system/capabilities` | `GET` | Inspect active model providers and hardware status |

---

## 9. Audit Reports & Technical Documentation

Exhaustive audit and engineering reports are available in `docs/`:

### Audit Reports (`docs/audit/`)
- [`docs/audit/FINAL_AUDIT_REPORT.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/FINAL_AUDIT_REPORT.md): Comprehensive executive summary, verification evidence, and final signoff.
- [`docs/audit/REMEDIATION_LOG.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/REMEDIATION_LOG.md): Detailed itemized log of all 9 security, architectural, and quality fixes.
- [`docs/audit/SECURITY_AUDIT.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/SECURITY_AUDIT.md): Security analysis, BOLA/IDOR remediation, and threat models.
- [`docs/audit/ARCHITECTURE_GAP_MATRIX.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/ARCHITECTURE_GAP_MATRIX.md): Traceability matrix covering Sections 6.1 through 6.10.
- [`docs/audit/ARTISTIC_FIDELITY_READINESS.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/ARTISTIC_FIDELITY_READINESS.md): Visual fidelity audit and benchmark rubric.
- [`docs/audit/DEPLOYMENT_READINESS.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/DEPLOYMENT_READINESS.md): PostgreSQL migration, async lifecycle, and container decoupling analysis.
- [`docs/audit/BASELINE_REPORT.md`](file:///c:/Users/patak/SerializationAssistant/docs/audit/BASELINE_REPORT.md): Initial baseline inventory and test execution report.

### Core Architecture (`docs/`)
- [`docs/ARCHITECTURE.md`](file:///c:/Users/patak/SerializationAssistant/docs/ARCHITECTURE.md): Service boundaries, modular monolith design, and background workers.
- [`docs/DATA_MODEL.md`](file:///c:/Users/patak/SerializationAssistant/docs/DATA_MODEL.md): Relational schemas, versioning rules, and ER diagrams.
- [`docs/MODEL_EVALUATION.md`](file:///c:/Users/patak/SerializationAssistant/docs/MODEL_EVALUATION.md): Fixed visual benchmark rubric, scoring, and candidate matrix.
- [`docs/TESTING.md`](file:///c:/Users/patak/SerializationAssistant/docs/TESTING.md): Acceptance testing methodology.
- [`docs/SECURITY.md`](file:///c:/Users/patak/SerializationAssistant/docs/SECURITY.md): Prompt injection defense, path traversal guards, and privacy boundaries.
- [`docs/ROADMAP.md`](file:///c:/Users/patak/SerializationAssistant/docs/ROADMAP.md): Future expansion roadmap.

---

## 10. License

Distributed under the Apache 2.0 License. See `LICENSE` for details.

