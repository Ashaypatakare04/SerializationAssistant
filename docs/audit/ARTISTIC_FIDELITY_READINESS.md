# Artistic Fidelity Readiness Audit

**Project:** AI Novel-to-Webtoon Studio  
**Audit Date:** 2026-10-22  
**Auditor:** Antigravity AI Systems Engineer & Technical Product Owner  

---

## 1. Executive Conclusion: Workflow vs Visual Fidelity

> [!IMPORTANT]
> **Key Finding:** The repository currently implements a **complete, verified end-to-end creative workflow**, but visual output is currently driven by a **deterministic, procedural Pillow graphics synthesizer** (in mock mode) rather than live diffusion model inference.
>
> **The procedural mock generator successfully proves layout, panel pacing, dialogue overlays, camera shot types, and approval gates. However, it does NOT prove artistic style fidelity, fine anatomical line rendering, or zero-shot character identity consistency.**

---

## 2. Current Image-Generation Mode

- **Active Provider:** `mock` (`MockImageProvider` in `backend/app/providers/mock_provider.py`).
- **Engine:** Python Pillow (PIL) Graphics Synthesizer running on CPU.
- **Visual Artifacts Produced:**
  - 800x1000px (4:5) webtoon comic panels.
  - Procedural vertical atmospheric gradients based on extracted hex palettes (e.g. `#1A1D24`, `#2E3A4D`).
  - Dark cinematic vignettes and directional rim lighting lines.
  - Character silhouettes with height variations and action pose lines.
  - Camera shot framing grids (medium shot, extreme close-up, Dutch angle).
  - Explicit watermarks: `[MOCK VISUAL ENGINE - DEV/TEST MODE]`.

---

## 3. Real Providers Detected & Capability Assessment

| Provider Adapter | Supported Models | Current Status | Capabilities Verified | Implementation Gap / Blocker |
|---|---|---|---|---|
| **Mock Provider** | Pillow Procedural Synthesizer | **Active & Verified** | Aspect ratios (`4:5`, `3:4`, `1:1`, `9:16`), inpainting region annotations, zero cost. | Does not generate photographic/manhwa artwork; procedural graphics only. |
| **OpenAI Adapter** | GPT-4o (Vision) + DALL-E 3 | In Codebase / Unconfigured | Schema definition, cost estimation ($0.04 draft, $0.08 final). | Requires live `OPENAI_API_KEY`. Live DALL-E 3 API calls raise `NotImplementedError`. Reference image conditioning requires multi-modal GPT-4o image generation or image-to-image endpoints. |
| **Gemini Adapter** | Gemini 1.5 Pro / Flash | In Codebase / Unconfigured | Multi-modal prompt structuring, style analysis from image references. | Requires live `GEMINI_API_KEY`. Image generation requires Imagen 3 integration. |
| **Stability AI Adapter**| SD3 / Stable Diffusion Core | In Codebase / Unconfigured | Multi-aspect ratio, inpainting, controlnet. | Requires live `STABILITY_API_KEY`. |
| **Local Diffusion** | AUTOMATIC1111 / ComfyUI / Diffusers | Config parameter in `.env.example` | Endpoint configuration. | Adapter implementation deferred for prototype. |

---

## 4. Reference Image & Character Sheet Propagation Audit

### Finding on Reference Propagation:
1. **Visual Style References:**
   - Visual style references uploaded by the user are stored in `storage/references/` with dimensions, role, and label.
   - In `style_analysis_service.run_style_analysis`, reference descriptions and metadata are extracted into a `StyleProfile` and versioned.
   - In `job_runner.py`, the active style profile's linework, palette, and shading rules are extracted and passed to `img_provider.generate_draft` and `img_provider.generate_final`.
2. **Character Sheet References (DEFECT IDENTIFIED):**
   - In the initial baseline `backend/app/workers/job_runner.py:219, 226`, `character_refs=[]` was hardcoded to an empty list!
   - This meant that even if a creator uploaded canonical character reference sheets and linked them via `CharacterReference`, the background generation worker never retrieved those references or passed them to the provider!
   - **Remediation Action in Phase 8:** Query all characters present in the panel/scene, fetch their approved primary `CharacterReference` assets, and supply their storage paths and descriptors to the generation call.

---

## 5. Inpainting & Correction Controls

- `POST /api/v1/assets/{asset_id}/edit-jobs` exists and accepts `instruction`, `target_region`, and `mask_storage_key`.
- In `mock_provider.py`, `edit_image` renders a targeted yellow inpainting correction box over the specified region (e.g., `face`, `left_hand`, `background`), increments the asset version, and saves the new version.
- This proves targeted asset version lineage, parent-child asset tracking, and approval reset upon modification.

---

## 6. Visual Quality Benchmark Harness

To evaluate real model outputs objectively without confusing structural unit tests with artistic fidelity:
- An independent benchmark harness script (`scripts/visual_benchmark.py`) is added.
- The benchmark records:
  1. `test_case_id`: e.g., `pilot_panel_01_minjun_rain`.
  2. `prompt_manifest`: Detailed text prompt, style profile tokens, and negative prompts.
  3. `reference_inputs`: File hashes of character sheets and style references used.
  4. `model_name`: Provider and exact model ID used.
  5. `human_evaluation_rubric`:
     - **Linework Adherence** (1-5): Does ink weight match the reference?
     - **Palette Fidelity** (1-5): Does shading match the reference palette?
     - **Facial/Anatomical Consistency** (1-5): Does the character look identical across panels?
     - **Composition Intent** (1-5): Does the shot match camera angle and framing?

---

## 7. Next Steps for Commercial High-Fidelity Rendering

1. **Configure ComfyUI / Stable Diffusion IP-Adapter Pipeline:**
   - Use IP-Adapter Plus (FaceID) for zero-shot character consistency across panels.
   - Use ControlNet (Openpose / Depth / Lineart) to force panel composition and anatomy to match storyboard sketches.
2. **Establish Fixed Reference Embeddings:**
   - Compute CLIP visual embeddings for approved style sheets and cache them in the style profile to eliminate style drift.
3. **Conduct Double-Blind Human Review:**
   - Have webtoon art directors score pilot panels using the benchmark rubric before authorizing full episode batch generation.
