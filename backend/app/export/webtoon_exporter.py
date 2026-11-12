import io
import json
import zipfile
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

# Protect against decompression bomb while allowing long webtoon strips
Image.MAX_IMAGE_PIXELS = 100_000_000

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.adaptation import Episode, Scene, Beat, Panel, DialogueSegment
from backend.app.models.asset import Asset, AssetVersion, Export
from backend.app.services.storage import storage_service


def wrap_dialogue_text(text: str, max_chars_per_line: int = 30) -> List[str]:
    """Wraps dialogue text into cleanly sized lines for speech balloons."""
    if not text:
        return [""]
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        # Break individual words that exceed maximum line width
        while len(w) > max_chars_per_line:
            chunk = w[:max_chars_per_line]
            if current_line:
                lines.append(" ".join(current_line))
                current_line = []
                current_len = 0
            lines.append(chunk)
            w = w[max_chars_per_line:]
        if not w:
            continue
        if current_len + len(w) + (1 if current_line else 0) <= max_chars_per_line:
            current_line.append(w)
            current_len += len(w) + (1 if len(current_line) > 1 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return lines or [text]


def composite_dialogue_bubbles(
    image: Image.Image,
    dialogues: List[DialogueSegment],
    panel_top_y: int = 0,
    font: Optional[ImageFont.ImageFont] = None
) -> None:
    """
    Renders styled speech balloons, thought clouds, captions, and SFX lettering
    directly onto the given PIL Image.
    """
    if not dialogues:
        return

    draw = ImageDraw.Draw(image)
    f = font or ImageFont.load_default(size=14)
    w, h = image.size

    # Position dialogues with offset stagger to avoid overlap
    y_offset = panel_top_y + 24
    for idx, d in enumerate(dialogues):
        seg_type = (d.segment_type or "speech_bubble").lower()
        speaker = d.speaker_name or ""
        lines = wrap_dialogue_text(d.text_content, max_chars_per_line=28)

        # Compute balloon dimensions
        max_line_len = max(len(l) for l in lines)
        bubble_w = min(max(max_line_len * 9 + 32, 140), w - 60)
        line_h = 18
        bubble_h = len(lines) * line_h + (22 if speaker else 0) + 16

        # Alternate left / right placement
        is_left = (idx % 2 == 0)
        bx = 30 if is_left else (w - bubble_w - 30)
        by = y_offset

        if seg_type == "caption":
            # Narrative caption box (parchment/dark slate box with gold/white lettering)
            draw.rectangle(
                [bx, by, bx + bubble_w, by + bubble_h - 4],
                fill=(15, 23, 42, 230),
                outline=(99, 102, 241),
                width=1
            )
            text_y = by + 8
            if speaker:
                draw.text((bx + 12, text_y), f"[{speaker.upper()}]", font=f, fill=(165, 180, 252))
                text_y += 18
            for l in lines:
                draw.text((bx + 12, text_y), l, font=f, fill=(241, 245, 249))
                text_y += line_h

        elif seg_type in ("thought", "thought_bubble"):
            # Thought bubble (cloud balloon with trailing bubbles)
            draw.rounded_rectangle(
                [bx, by, bx + bubble_w, by + bubble_h],
                radius=18,
                fill=(255, 255, 255),
                outline=(71, 85, 105),
                width=2
            )
            # Trailing bubbles pointing towards character
            tail_x = bx + 25 if is_left else bx + bubble_w - 25
            draw.ellipse([tail_x - 5, by + bubble_h + 3, tail_x + 5, by + bubble_h + 13], fill=(255, 255, 255), outline=(71, 85, 105))
            draw.ellipse([tail_x - 3, by + bubble_h + 16, tail_x + 3, by + bubble_h + 22], fill=(255, 255, 255), outline=(71, 85, 105))

            text_y = by + 8
            if speaker:
                draw.text((bx + 14, text_y), f"({speaker})", font=f, fill=(100, 116, 139))
                text_y += 18
            for l in lines:
                draw.text((bx + 14, text_y), l, font=f, fill=(30, 41, 59))
                text_y += line_h

        elif seg_type in ("sfx", "sound_effect"):
            # Sound Effect dynamic badge
            draw.rectangle(
                [bx, by, bx + bubble_w, by + bubble_h - 6],
                fill=(220, 38, 38, 230),
                outline=(254, 240, 138),
                width=2
            )
            draw.text((bx + 14, by + 8), f"SFX: {d.text_content.upper()}", font=f, fill=(254, 240, 138))

        else:
            # Standard Webtoon Speech Balloon with Pointer Tail
            # Drop shadow
            draw.rounded_rectangle(
                [bx + 2, by + 2, bx + bubble_w + 2, by + bubble_h + 2],
                radius=14,
                fill=(0, 0, 0, 70)
            )
            # Balloon body
            draw.rounded_rectangle(
                [bx, by, bx + bubble_w, by + bubble_h],
                radius=14,
                fill=(255, 255, 255),
                outline=(20, 24, 32),
                width=2
            )
            # Triangular pointer tail
            tail_x = bx + 22 if is_left else bx + bubble_w - 38
            draw.polygon(
                [(tail_x, by + bubble_h - 1), (tail_x + 16, by + bubble_h - 1), (tail_x + 6, by + bubble_h + 12)],
                fill=(255, 255, 255)
            )
            draw.line([(tail_x, by + bubble_h - 1), (tail_x + 6, by + bubble_h + 12)], fill=(20, 24, 32), width=2)
            draw.line([(tail_x + 6, by + bubble_h + 12), (tail_x + 16, by + bubble_h - 1)], fill=(20, 24, 32), width=2)

            text_y = by + 8
            if speaker:
                draw.text((bx + 14, text_y), speaker.upper(), font=f, fill=(79, 70, 229))
                text_y += 18
            for l in lines:
                draw.text((bx + 14, text_y), l, font=f, fill=(15, 23, 42))
                text_y += line_h

        y_offset += bubble_h + 18


class WebtoonExporter:
    MAX_SLICE_HEIGHT = 8000  # Standard maximum mobile webtoon slice height in px

    @classmethod
    async def export_episode(
        cls,
        db: AsyncSession,
        episode_id: str,
        require_all_approved: bool = True,
        include_speech_bubbles: bool = True
    ) -> Export:
        # Load episode with panels and dialogue
        stmt = (
            select(Episode)
            .options(
                selectinload(Episode.scenes).selectinload(Scene.beats).selectinload(Beat.panels).selectinload(Panel.dialogues)
            )
            .where(Episode.id == episode_id)
        )
        res = await db.execute(stmt)
        episode = res.scalar_one_or_none()
        if not episode:
            raise ValueError(f"Episode {episode_id} not found.")

        # Get adaptation plan for project ID
        from backend.app.models.adaptation import AdaptationPlan
        plan_stmt = select(AdaptationPlan).where(AdaptationPlan.id == episode.adaptation_plan_id)
        plan_res = await db.execute(plan_stmt)
        plan = plan_res.scalar_one_or_none()
        project_id = plan.project_id

        # Collect panels in strict numerical reading order
        all_panels: List[Panel] = []
        for s in episode.scenes:
            for b in s.beats:
                all_panels.extend(b.panels)
        all_panels.sort(key=lambda p: p.panel_number)

        if not all_panels:
            raise ValueError(f"Cannot export: Episode {episode.title} has no storyboard panels.")

        # Load images for each panel
        panel_images: List[Tuple[Panel, Image.Image]] = []
        missing_assets = []
        unapproved_panels = []

        for p in all_panels:
            if require_all_approved and not p.is_approved:
                unapproved_panels.append(p.panel_number)

            img: Image.Image = None
            if p.active_asset_id:
                # Load asset version
                ver_stmt = (
                    select(AssetVersion)
                    .where(AssetVersion.asset_id == p.active_asset_id)
                    .order_by(AssetVersion.version_number.desc())
                )
                ver_res = await db.execute(ver_stmt)
                latest_ver = ver_res.scalars().first()
                if latest_ver:
                    try:
                        raw_bytes = storage_service.read_bytes(latest_ver.storage_key)
                        img = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
                    except Exception:
                        img = None

            if img is None:
                missing_assets.append(p.panel_number)
                # Fallback: create placeholder panel
                img = Image.new("RGB", (800, 1000), color=(30, 34, 42))
                d = ImageDraw.Draw(img)
                d.rectangle([10, 10, 790, 990], outline=(100, 100, 120), width=3)
                d.text((40, 480), f"Panel {p.panel_number} (Asset missing or in progress)", fill=(200, 200, 200))

            panel_images.append((p, img))

        if require_all_approved and unapproved_panels:
            raise ValueError(f"Cannot export: Panels {unapproved_panels} have not received explicit creator approval.")

        if require_all_approved and missing_assets:
            raise ValueError(f"Cannot export: Missing illustrations for panels {missing_assets}. All panel illustrations must be generated and approved before export.")

        # Prepare stitched long strip(s) via streaming memory-efficient slicing
        standard_width = 800
        margin = 20
        target_w = standard_width - (margin * 2)
        total_height = 0
        slice_idx = 1
        current_y = 20
        manifest_panels = []
        font = ImageFont.load_default(size=14)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            current_slice_img = Image.new("RGB", (standard_width, cls.MAX_SLICE_HEIGHT), color=(18, 20, 26))

            for p, orig_img in panel_images:
                # If speech bubbles are enabled, create a lettered version of individual panel
                lettered_panel_img = orig_img.copy()
                if include_speech_bubbles and p.dialogues:
                    composite_dialogue_bubbles(lettered_panel_img, p.dialogues, panel_top_y=10, font=font)

                # Stream individual panel PNG into ZIP immediately
                p_buf = io.BytesIO()
                lettered_panel_img.save(p_buf, format="PNG")
                zf.writestr(f"panels/panel_{p.panel_number:02d}.png", p_buf.getvalue())
                del p_buf
                del lettered_panel_img

                # Resize proportionally to match standard width (accounting for webtoon margins)
                aspect = orig_img.height / orig_img.width
                target_h = int(target_w * aspect)
                resized = orig_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # Check if adding this panel + vertical spacing exceeds current slice height
                spacing = p.vertical_spacing_after_px or 40
                if current_y + target_h + spacing > cls.MAX_SLICE_HEIGHT:
                    # Flush completed slice to ZIP and allocate fresh slice canvas
                    cropped = current_slice_img.crop((0, 0, standard_width, current_y))
                    s_buf = io.BytesIO()
                    cropped.save(s_buf, format="JPEG", quality=92)
                    zf.writestr(f"slices/webtoon_slice_{slice_idx:02d}.jpg", s_buf.getvalue())
                    del s_buf
                    del cropped
                    del current_slice_img

                    total_height += current_y
                    slice_idx += 1
                    current_slice_img = Image.new("RGB", (standard_width, cls.MAX_SLICE_HEIGHT), color=(18, 20, 26))
                    current_y = 20

                # Paste panel onto slice
                current_slice_img.paste(resized, (margin, current_y))
                del resized
                
                # Overlay speech bubbles and lettering onto continuous slice if enabled
                if include_speech_bubbles and p.dialogues:
                    composite_dialogue_bubbles(current_slice_img, p.dialogues, panel_top_y=current_y, font=font)

                manifest_panels.append({
                    "panel_number": p.panel_number,
                    "slice_index": slice_idx,
                    "y_offset_in_slice": current_y,
                    "height": target_h,
                    "shot_type": p.shot_type,
                    "dialogue_count": len(p.dialogues)
                })

                current_y += target_h + spacing

            # Flush final slice to ZIP
            if current_y > 20:
                cropped = current_slice_img.crop((0, 0, standard_width, current_y))
                s_buf = io.BytesIO()
                cropped.save(s_buf, format="JPEG", quality=92)
                zf.writestr(f"slices/webtoon_slice_{slice_idx:02d}.jpg", s_buf.getvalue())
                del s_buf
                del cropped
                del current_slice_img
                total_height += current_y
                final_slice_count = slice_idx
            else:
                final_slice_count = slice_idx - 1

            # Write manifest.json
            manifest_data = {
                "project_id": project_id,
                "episode_id": episode_id,
                "episode_title": episode.title,
                "total_panels": len(all_panels),
                "total_height_px": total_height,
                "width_px": standard_width,
                "slice_count": final_slice_count,
                "include_speech_bubbles": include_speech_bubbles,
                "panels": manifest_panels
            }
            zf.writestr("manifest.json", json.dumps(manifest_data, indent=2))

        # Save ZIP archive to storage service
        zip_bytes = zip_buf.getvalue()
        storage_key, chk, fsize = storage_service.save_bytes(
            "exports",
            f"webtoon_{episode_id[:8]}_ep{episode.episode_number:02d}.zip",
            zip_bytes
        )

        export_record = Export(
            project_id=project_id,
            episode_id=episode_id,
            storage_key=storage_key,
            total_height_px=total_height,
            slice_count=final_slice_count,
            panel_count=len(all_panels),
            manifest_data=manifest_data
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        return export_record

webtoon_exporter = WebtoonExporter()
