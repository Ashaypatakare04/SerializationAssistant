import io
import json
import zipfile
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.adaptation import Episode, Scene, Beat, Panel, DialogueSegment
from backend.app.models.asset import Asset, AssetVersion, Export
from backend.app.services.storage import storage_service

class WebtoonExporter:
    MAX_SLICE_HEIGHT = 8000  # Standard maximum mobile webtoon slice height in px

    @classmethod
    async def export_episode(
        cls,
        db: AsyncSession,
        episode_id: str,
        require_all_approved: bool = True
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


        # Prepare stitched long strip(s)
        # 1. Calculate dimensions
        standard_width = 800
        total_height = 0
        prepared_slices: List[Image.Image] = []
        
        current_slice_img = Image.new("RGB", (standard_width, cls.MAX_SLICE_HEIGHT), color=(18, 20, 26))
        current_y = 20
        slice_idx = 1
        manifest_panels = []

        for p, orig_img in panel_images:
            # Resize proportionally to match standard width (accounting for webtoon margins)
            margin = 20
            target_w = standard_width - (margin * 2)
            aspect = orig_img.height / orig_img.width
            target_h = int(target_w * aspect)
            resized = orig_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # Check if adding this panel + vertical spacing exceeds current slice height
            spacing = p.vertical_spacing_after_px
            if current_y + target_h + spacing > cls.MAX_SLICE_HEIGHT:
                # Crop current slice to actual used height and start new slice
                cropped = current_slice_img.crop((0, 0, standard_width, current_y))
                prepared_slices.append(cropped)
                total_height += current_y
                current_slice_img = Image.new("RGB", (standard_width, cls.MAX_SLICE_HEIGHT), color=(18, 20, 26))
                current_y = 20
                slice_idx += 1

            # Paste panel onto slice
            current_slice_img.paste(resized, (margin, current_y))
            
            # Overlay dialogue/captions if present
            draw = ImageDraw.Draw(current_slice_img)
            for d in p.dialogues:
                d_text = f"{d.speaker_name + ': ' if d.speaker_name else ''}{d.text_content}"
                if d.segment_type == "caption":
                    draw.rectangle([margin + 20, current_y + 20, margin + 20 + min(len(d_text) * 7 + 20, target_w - 40), current_y + 55], fill=(0, 0, 0, 200), outline=(255, 255, 255))
                    draw.text((margin + 30, current_y + 30), d_text, fill=(255, 255, 255))
                elif d.segment_type == "speech_bubble":
                    draw.rounded_rectangle([margin + 30, current_y + target_h - 70, margin + 30 + min(len(d_text) * 7 + 30, target_w - 60), current_y + target_h - 25], radius=10, fill=(255, 255, 255), outline=(0, 0, 0), width=2)
                    draw.text((margin + 42, current_y + target_h - 60), d_text, fill=(10, 10, 10))

            manifest_panels.append({
                "panel_number": p.panel_number,
                "slice_index": slice_idx,
                "y_offset_in_slice": current_y,
                "height": target_h,
                "shot_type": p.shot_type,
                "dialogue_count": len(p.dialogues)
            })

            current_y += target_h + spacing

        # Crop and save final slice
        if current_y > 20:
            cropped = current_slice_img.crop((0, 0, standard_width, current_y))
            prepared_slices.append(cropped)
            total_height += current_y

        # Package into export ZIP: slices + individual panels + manifest.json
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Write slices
            for s_i, sl_img in enumerate(prepared_slices):
                buf = io.BytesIO()
                sl_img.save(buf, format="JPEG", quality=92)
                zf.writestr(f"slices/webtoon_slice_{s_i + 1:02d}.jpg", buf.getvalue())

            # Write individual panels
            for p, p_img in panel_images:
                buf = io.BytesIO()
                p_img.save(buf, format="PNG")
                zf.writestr(f"panels/panel_{p.panel_number:02d}.png", buf.getvalue())

            # Write manifest.json
            manifest_data = {
                "project_id": project_id,
                "episode_id": episode_id,
                "episode_title": episode.title,
                "total_panels": len(all_panels),
                "total_height_px": total_height,
                "width_px": standard_width,
                "slice_count": len(prepared_slices),
                "format": "vertical_webtoon_standard",
                "panels": manifest_panels
            }
            zf.writestr("manifest.json", json.dumps(manifest_data, indent=2))

        zip_bytes = zip_buf.getvalue()
        storage_key, checksum, file_size = storage_service.save_bytes(
            "exports",
            f"webtoon_{episode.id[:8]}_export.zip",
            zip_bytes
        )

        export_record = Export(
            project_id=project_id,
            episode_id=episode_id,
            export_format="vertical_webtoon_zip",
            storage_key=storage_key,
            manifest_data=manifest_data,
            panel_count=len(all_panels),
            total_height_px=total_height,
            slice_count=len(prepared_slices),
            is_verified=True
        )
        db.add(export_record)
        await db.commit()
        await db.refresh(export_record)
        return export_record

webtoon_exporter = WebtoonExporter()
