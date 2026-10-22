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

## 5. Running Automated Acceptance Tests

The test suite validates all 12 non-negotiable acceptance tests:

```bash
# Run complete backend test suite
.\backend\venv\Scripts\pytest backend\tests -v -W ignore

# Run Next.js production build verification
cd frontend && npm run build
```

### Test Coverage Summary (12/12 Passed)
- **Test 1**: Story fidelity & character preservation with source locators.
- **Test 2**: Reference isolation (style extracted without narrative borrowing).
- **Test 3**: Style profile versioning & attribute modifications.
- **Test 4**: Canonical character appearance consistency across panels.
- **Test 5**: Beat-level emotional direction changes without visual drift.
- **Test 6**: Approval gate enforcement (blocks final generation until approved).
- **Test 7**: Targeted revision safety (modifying one panel preserves others).
- **Test 8**: Stale background job overwrite guard.
- **Test 9**: Server restart job recovery from running state.
- **Test 10**: Vertical webtoon slice stitching, manifest, and ZIP export.
- **Test 11**: Security checks (path traversal rejection, upload file size limits).
- **Test 12**: Real provider capability detection and transparent mock reporting.

---

## 6. API Reference

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
| `/api/v1/episodes/{id}/export-jobs` | `POST` | Compile vertical webtoon slices and export ZIP |
| `/api/v1/system/capabilities` | `GET` | Inspect active model providers and hardware status |

---

## 7. Technical Documentation

Detailed architectural reports are available in the `docs/` directory:
- [`docs/ARCHITECTURE.md`](file:///c:/Users/patak/SerializationAssistant/docs/ARCHITECTURE.md): Service boundaries, modular monolith design, and background workers.
- [`docs/DATA_MODEL.md`](file:///c:/Users/patak/SerializationAssistant/docs/DATA_MODEL.md): Relational schemas, versioning rules, and ER diagrams.
- [`docs/MODEL_EVALUATION.md`](file:///c:/Users/patak/SerializationAssistant/docs/MODEL_EVALUATION.md): Fixed visual benchmark rubric, scoring, and candidate matrix.
- [`docs/TESTING.md`](file:///c:/Users/patak/SerializationAssistant/docs/TESTING.md): Verification report covering all 12 acceptance tests.
- [`docs/SECURITY.md`](file:///c:/Users/patak/SerializationAssistant/docs/SECURITY.md): Prompt injection defense, path traversal guards, and privacy boundaries.
- [`docs/ROADMAP.md`](file:///c:/Users/patak/SerializationAssistant/docs/ROADMAP.md): Future expansion (LoRA training, multi-episode scaling, and Webtoon Canvas publishing).

---

## 8. License

Distributed under the Apache 2.0 License. See `LICENSE` for details.
