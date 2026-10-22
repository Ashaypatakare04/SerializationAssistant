# Product Roadmap & Scaling Architecture

## Phase 1: Working Vertical Slice (Completed)
- [x] Ingest text and markdown manuscripts with chapter partitioning.
- [x] Extract structured Story Bible (premise, tone, world rules, canonical characters, events, continuity).
- [x] Reference upload with role tagging (`visual_style`, `character_identity`, `layout`, `environment`).
- [x] Extract versioned Visual Style Profile with strict reference isolation.
- [x] Serialization planning with beat-level emotional progressions (intensity 1-10, trajectory, constraints).
- [x] Storyboard editor with shot types, camera angles, focal points, and separate lettering layers.
- [x] Human creator approval gates enforced on Story Bible, Style Profile, Plan, and Storyboard.
- [x] Provider-independent generation engine with deterministic offline Mock Provider (Pillow synthesizer).
- [x] Stale background job protection and server restart recovery.
- [x] Narrative, Visual, and Sequence automated QA audits.
- [x] Vertical webtoon reader simulation with continuous scroll and speech bubble overlays.
- [x] Mobile-optimized vertical strip slice compiler and export package with `manifest.json`.
- [x] 12/12 Automated Acceptance Tests passing.

---

## Phase 2: Long-Form Production Scaling (Q2 2027)
- **Multi-Episode Story Arcs**: Extend serialization planning across multi-chapter season volumes with continuity dependency graphs.
- **Durable Redis / Celery Worker Queue**: Upgrade the local background runner to an enterprise Redis-backed task queue for distributed GPU rendering nodes.
- **PostgreSQL / S3 Cloud Persistence**: Transition SQLite and local filesystem storage to managed AWS S3 / Google Cloud Storage and RDS PostgreSQL.

---

## Phase 3: Character & Style Fine-Tuning (Q3 2027)
- **Creator LoRA Adapter Training**: Train lightweight Low-Rank Adaptation (LoRA) weights directly on approved reference sheets to lock character facial structures across thousands of panels.
- **ControlNet Integration**: Support open-pose skeleton and line-art depth conditioning for dynamic comic action sequences.
- **Vector Speech Bubble Editor**: Interactive canvas for dragging, resizing, and styling manga speech tails and custom typographic sound effects.

---

## Phase 4: Commercial Platform & Social Publishing (Q4 2027)
- **Multi-Creator Collaboration**: Real-time collaborative workspace for writer, line artist, colorist, and art director.
- **Direct Webtoon Platform Publishing**: 1-click publishing adapters for Webtoon Canvas, Tapas, and KakaoPage format specifications.
- **Audience Metrics & Reader Analytics**: Non-intrusive scroll velocity and drop-off analytics informing future episode pacing proposals without silently overriding approved creator canon.
