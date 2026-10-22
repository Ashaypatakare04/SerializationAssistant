import io
import re
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from backend.app.providers.base import BaseLLMProvider, BaseImageProvider

class MockLLMProvider(BaseLLMProvider):
    async def analyze_story(self, manuscript_text: str, project_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deterministic, structured story extraction from manuscript text.
        Finds character names, dialogue, setting, events, and continuity constraints.
        """
        lines = [line.strip() for line in manuscript_text.splitlines() if line.strip()]
        
        # Simple extraction heuristics for deterministic testing
        # 1. Look for capitalized character dialogue patterns: NAME: or "...", Name said
        found_names = set()
        for line in lines:
            m = re.match(r"^([A-Z][a-zA-Z]{2,15}):", line)
            if m:
                found_names.add(m.group(1))
            m2 = re.search(r"([A-Z][a-zA-Z]{2,15})\s+(said|whispered|shouted|murmured|smiled|frowned)", line)
            if m2:
                found_names.add(m2.group(1))

        if not found_names:
            found_names = {"Min-jun", "Soo-jin"}

        character_list = []
        name_list = sorted(list(found_names))
        for idx, name in enumerate(name_list):
            is_protagonist = (idx == 0)
            character_list.append({
                "canonical_name": name,
                "aliases": [name[:3], f"{name}-ah"] if len(name) > 3 else [],
                "role": "protagonist" if is_protagonist else "supporting",
                "personality_summary": f"Determined, observant, carrying hidden tension." if is_protagonist else "Loyal, witty, sharp-tongued.",
                "voice_and_mannerisms": "Speaks carefully, pauses before delivering important truths.",
                "physical_appearance": f"Sharp eyes, athletic build, messy dark hair." if is_protagonist else "Warm smile, tailored jacket, expressive eyebrows.",
                "hair_style_and_color": "Raven black, parted slightly" if is_protagonist else "Chestnut brown, tied back",
                "clothing_and_accessories": "Slate gray trench coat, silver signet ring" if is_protagonist else "Cream knitted sweater, wristwatch",
                "distinctive_features": "Faint scar near left brow" if is_protagonist else "Dimple on right cheek",
                "body_proportions": "7.5 heads athletic manhwa proportion"
            })

        # Extract major events
        events = []
        for idx, line in enumerate(lines[:8]):
            events.append({
                "chronological_order": idx + 1,
                "title": f"Key Beat {idx + 1}: {line[:40]}...",
                "summary": line,
                "source_locator": f"Paragraph {idx + 1}",
                "emotional_weight": "high" if idx % 2 == 1 else "moderate"
            })

        relationships = []
        if len(name_list) >= 2:
            relationships.append({
                "source_character_name": name_list[0],
                "target_character_name": name_list[1],
                "relationship_type": "allies with underlying tension",
                "dynamics_description": "Shared history and mutual reliance tested by recent revelations."
            })

        continuity_facts = [
            {
                "category": "timeline",
                "statement": "The events occur over a single tense rainy evening in Seoul.",
                "source_locator": "Section 1",
                "is_confirmed": True
            },
            {
                "category": "rule",
                "statement": "Neither character knows about the sealed dossier until it is opened.",
                "source_locator": "Section 2",
                "is_confirmed": True
            }
        ]

        return {
            "premise": "A tense atmospheric encounter unraveling long-held secrets between two estranged companions.",
            "genre": project_config.get("genre", "Urban Mystery / Drama"),
            "target_audience": project_config.get("target_audience", "Young Adult / Mature Fiction"),
            "narrative_tone": "Moody, cinematic, emotionally charged with dry comedic relief.",
            "world_rules": [
                {"rule": "Grounded reality with stylized manhwa emotional expressiveness"},
                {"rule": "Weather mirrors internal psychological tension"}
            ],
            "themes": ["Loyalty", "Unspoken truth", "Cost of ambition"],
            "uncertainties": [
                {"aspect": "Character past history", "note": "Exact nature of their initial fallout is hinted at but not explicitly detailed."}
            ],
            "characters": character_list,
            "events": events,
            "relationships": relationships,
            "continuity_facts": continuity_facts
        }

    async def analyze_style(self, reference_descriptions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes visual references to extract a comprehensive style profile.
        Ensures strict style isolation without importing narrative elements.
        """
        return {
            "linework_and_contours": "Crisp dynamic digital ink lines with tapered stroke endings; thicker silhouettes on outer contours with delicate interior hatching for hair and fabric folds.",
            "anatomy_and_proportions": "Modern Korean manhwa aesthetic: elongated limbs (7.5 - 8 heads), expressive angular jawlines, structured clavicles and hands.",
            "facial_features_and_expressions": "Semi-realistic eye construction with delicate eyelashes, subtle lower lid definition, sharp iris reflections, and nuanced micro-expressions.",
            "palette_and_colors": ["#1A1D24", "#2E3A4D", "#7B8FA1", "#D9E2EC", "#D97706", "#991B1B"],
            "color_relationships": "Desaturated slate and navy base tones accented by targeted amber and crimson emotional focal points.",
            "shading_and_lighting": "Soft two-tone cell shading augmented by rim lighting and gentle atmospheric occlusion in shadowed crevices.",
            "texture_and_rendering": "Smooth digital painting with subtle paper grain texture overlay on backgrounds; sharp, clean edges on clothing materials.",
            "background_treatment": "Painterly architectural environments with deliberate gaussian focal blur on deep backgrounds to enhance character foreground readability.",
            "composition_conventions": "Vertical webtoon conventions: dynamic Dutch angles for suspense, dramatic vertical eye-tracking, breathing room spacing.",
            "degree_of_stylization": "High-fidelity modern manhwa serialization standard.",
            "reference_isolation_notes": "Extracted strictly aesthetic and rendering principles. No reference characters or story events imported.",
            "uncertainties": [
                {"item": "Chibi humor threshold", "recommendation": "Maintain grounded proportion; restrict cartoonish deformation to explicit comedic beats."}
            ]
        }

    async def propose_adaptation(self, story_bible_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Proposes serialization structure, episodes, scenes, and beat-level emotional progressions.
        """
        chars = story_bible_data.get("characters", [])
        char_names = [c["canonical_name"] for c in chars]
        p1 = char_names[0] if char_names else "Protagonist"
        p2 = char_names[1] if len(char_names) > 1 else "Companion"

        return {
            "title": "Season 1 Pilot Adaptation",
            "target_episodes_estimate": 1,
            "pacing_strategy": "Atmospheric slow burn opening leading to a sharp revelation climax",
            "story_bible_version": 1,
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "Episode 1: Shadows in the Rain",
                    "premise_and_purpose": "Establish the reunion between the characters and reveal the catalyst for their mission.",
                    "source_sections_covered": ["Section 1", "Section 2"],
                    "opening_hook": "A lone silhouette stands under the flickering streetlight, water dripping from a dark umbrella.",
                    "ending_cliffhanger_or_beat": "The document slides across the wet table, revealing a name neither expected to see.",
                    "target_panel_count": 8,
                    "scenes": [
                        {
                            "scene_number": 1,
                            "title": "Awkward Encounter at the Cafe",
                            "narrative_purpose": "Reintroduce the pair, contrasting their outward banter with underlying wariness.",
                            "environment": "Dimly lit vintage tea parlor with rain pattering against foggy glass",
                            "time_of_day": "evening",
                            "pacing_note": "Slow, measured dialogue pauses with comedic awkwardness giving way to tension",
                            "beats": [
                                {
                                    "beat_number": 1,
                                    "dominant_emotion": "Awkward Hesitation",
                                    "secondary_emotion": "Subtle Comedic Irony",
                                    "emotional_intensity": 4,
                                    "emotional_progression": "Stiff polite greeting -> dry comedic observation about ruined coat -> uneasy eye contact.",
                                    "narrative_action": f"{p1} and {p2} sit opposite each other, hesitating over who speaks first.",
                                    "visual_exaggeration_constraint": "Restrained realism; slight comedic eyebrow twitch without chibi distortion."
                                },
                                {
                                    "beat_number": 2,
                                    "dominant_emotion": "Rising Tension",
                                    "secondary_emotion": "Serious Realization",
                                    "emotional_intensity": 8,
                                    "emotional_progression": "Shifting posture -> direct confrontation -> sudden silence as the evidence is revealed.",
                                    "narrative_action": f"{p1} unzips their inner coat pocket, revealing the sealed envelope. {p2}'s expression hardens.",
                                    "visual_exaggeration_constraint": "High dramatic contrast, sharp dramatic eye reflections, deep shadows."
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    async def generate_storyboard(self, episode_data: Dict[str, Any], story_bible_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Creates an 8-panel pilot storyboard covering different shot types, emotional transitions,
        and vertical webtoon pacing.
        """
        chars = story_bible_data.get("characters", [])
        char_ids = [c["id"] for c in chars if "id" in c]
        char_names = [c["canonical_name"] for c in chars]
        p1 = char_names[0] if char_names else "Min-jun"
        p2 = char_names[1] if len(char_names) > 1 else "Soo-jin"

        panels = [
            {
                "panel_number": 1,
                "narrative_purpose": "Establish moody atmospheric setting and sense of isolation.",
                "shot_type": "wide_shot",
                "camera_angle": "high_angle",
                "composition_notes": "Rain-slicked alleyway viewed from above; neon reflections cutting through deep puddles.",
                "focal_point": "Flickering amber streetlamp beside the cafe doorway",
                "aspect_ratio": "4:5",
                "character_action": f"A dark silhouette holding a black umbrella steps toward the cafe door.",
                "expression_and_body_language": "Shoulders hunched against the cold wind.",
                "environment_and_background": "Cobblestone street, rain streaks, steam rising from grates.",
                "lighting_direction": "Top-down diffused streetlamp with deep edge shadows.",
                "local_emotion": "Melancholy anticipation",
                "vertical_spacing_after_px": 80,
                "dialogues": [
                    {"segment_type": "caption", "text_content": "Rain has a habit of washing away everything except what you want forgotten.", "order_in_panel": 1, "position_hint": "top_left"}
                ]
            },
            {
                "panel_number": 2,
                "narrative_purpose": "Show the interior threshold and establish character presence.",
                "shot_type": "medium_shot",
                "camera_angle": "eye_level",
                "composition_notes": f"Door opens; {p1} stands shaking rain droplets from their umbrella.",
                "focal_point": f"{p1}'s dripping coat and watchful eyes",
                "aspect_ratio": "4:5",
                "character_action": f"{p1} pauses at the entrance, scanning the quiet parlor.",
                "expression_and_body_language": "Guarded, weary gaze scanning corner booths.",
                "environment_and_background": "Warm wood interior, vintage brass lamps, raindrops on window panes.",
                "lighting_direction": "Warm amber interior rim lighting contrasting cold blue rain outside.",
                "local_emotion": "Cautious alertness",
                "vertical_spacing_after_px": 60,
                "dialogues": [
                    {"segment_type": "sound_effect", "text_content": "*CHIME*", "order_in_panel": 1, "position_hint": "top_right"}
                ]
            },
            {
                "panel_number": 3,
                "narrative_purpose": "Introduce the second character with a light dry comedic beat.",
                "shot_type": "medium_shot",
                "camera_angle": "low_angle",
                "composition_notes": f"{p2} is already seated at a corner booth, swirling a cup of hot tea.",
                "focal_point": f"{p2}'s half-smirk and steaming tea cup",
                "aspect_ratio": "4:5",
                "character_action": f"{p2} looks up from the cup, raising an eyebrow with dry amusement.",
                "expression_and_body_language": "Relaxed posture, leaning back against leather cushion.",
                "environment_and_background": "Corner leather booth, small wooden table with teapot.",
                "lighting_direction": "Soft pendant light directly above table.",
                "local_emotion": "Dry comedic sarcasm",
                "vertical_spacing_after_px": 50,
                "dialogues": [
                    {"segment_type": "speech_bubble", "speaker_name": p2, "text_content": "You're seven minutes late. I almost drank the expensive tea without you.", "order_in_panel": 1, "position_hint": "top_right"}
                ]
            },
            {
                "panel_number": 4,
                "narrative_purpose": "Two-shot establishing mutual awkwardness and unresolved history.",
                "shot_type": "medium_shot",
                "camera_angle": "eye_level",
                "composition_notes": "Both characters across table; symmetrical framing emphasizing distance.",
                "focal_point": "The empty space on the table between them",
                "aspect_ratio": "4:5",
                "character_action": f"{p1} takes off coat and sits down stiffly.",
                "expression_and_body_language": "Tense posture, both avoiding immediate direct gaze.",
                "environment_and_background": "Cafe booth, steam rising between them.",
                "lighting_direction": "Balanced warm interior glow.",
                "local_emotion": "Awkward hesitation",
                "vertical_spacing_after_px": 70,
                "dialogues": [
                    {"segment_type": "speech_bubble", "speaker_name": p1, "text_content": "The traffic was stopped near the bridge. You haven't changed.", "order_in_panel": 1, "position_hint": "top_left"},
                    {"segment_type": "speech_bubble", "speaker_name": p2, "text_content": "Neither have you. Still wearing the same battered trench coat.", "order_in_panel": 2, "position_hint": "bottom_right"}
                ]
            },
            {
                "panel_number": 5,
                "narrative_purpose": "Close-up reaction highlighting emotional transition from humor to seriousness.",
                "shot_type": "close_up",
                "camera_angle": "eye_level",
                "composition_notes": f"Tight frame on {p1}'s eyes; smile fades into solemn concentration.",
                "focal_point": f"{p1}'s sharp eyes and subtle facial tension",
                "aspect_ratio": "4:5",
                "character_action": f"{p1} stops smiling and leans forward across the table.",
                "expression_and_body_language": "Narrowed eyes, jaw set with serious intent.",
                "environment_and_background": "Blurred background bokeh with raindrops on window.",
                "lighting_direction": "Side directional light creating sharp cheekbone shadow.",
                "local_emotion": "Transition to grave seriousness",
                "vertical_spacing_after_px": 60,
                "dialogues": [
                    {"segment_type": "speech_bubble", "speaker_name": p1, "text_content": "I didn't call you here for tea, Soo-jin.", "order_in_panel": 1, "position_hint": "bottom_left"}
                ]
            },
            {
                "panel_number": 6,
                "narrative_purpose": "The reveal of the critical evidence item.",
                "shot_type": "close_up",
                "camera_angle": "high_angle",
                "composition_notes": "Hands sliding a wax-sealed black dossier onto the polished wooden table.",
                "focal_point": "The cracked red wax seal on the dossier",
                "aspect_ratio": "4:5",
                "character_action": f"{p1}'s leather-gloved fingers place the sealed file down.",
                "expression_and_body_language": "Decisive, deliberate hand gesture.",
                "environment_and_background": "Table surface, reflection of tea cup.",
                "lighting_direction": "Dramatic overhead spotlight casting sharp shadow.",
                "local_emotion": "Ominous suspense",
                "vertical_spacing_after_px": 80,
                "dialogues": [
                    {"segment_type": "sound_effect", "text_content": "*THUD*", "order_in_panel": 1, "position_hint": "center"}
                ]
            },
            {
                "panel_number": 7,
                "narrative_purpose": "Extreme close-up of second character's shocked realization.",
                "shot_type": "extreme_close_up",
                "camera_angle": "low_angle",
                "composition_notes": f"Dynamic crop on {p2}'s widening eyes as they recognize the insignia on the seal.",
                "focal_point": f"{p2}'s dilated pupil reflecting the seal symbol",
                "aspect_ratio": "4:5",
                "character_action": f"{p2}'s teacup freezes mid-air; knuckles turn white.",
                "expression_and_body_language": "Sudden shock, breath caught in throat.",
                "environment_and_background": "Dark background fading to deep vignette.",
                "lighting_direction": "Sharp underlighting accentuating astonishment.",
                "local_emotion": "Shock and dread",
                "vertical_spacing_after_px": 90,
                "dialogues": [
                    {"segment_type": "thought_bubble", "speaker_name": p2, "text_content": "That seal... it was supposed to be destroyed three years ago.", "order_in_panel": 1, "position_hint": "top_right"}
                ]
            },
            {
                "panel_number": 8,
                "narrative_purpose": "Episode climax and cliffhanger reveal.",
                "shot_type": "medium_shot",
                "camera_angle": "dutch_angle",
                "composition_notes": "Dramatic tilted angle; both characters locked in tense silent confrontation.",
                "focal_point": "The space between their locked gazes across the open folder",
                "aspect_ratio": "4:5",
                "character_action": f"{p2} reaches toward the document as lightning flashes outside.",
                "expression_and_body_language": "Trembling fingers, hardened resolve on both faces.",
                "environment_and_background": "Sudden bright lightning flash silhouetting the window frame.",
                "lighting_direction": "High-contrast rim flash cutting through deep cafe shadows.",
                "local_emotion": "High-intensity cliffhanger",
                "vertical_spacing_after_px": 120,
                "dialogues": [
                    {"segment_type": "speech_bubble", "speaker_name": p1, "text_content": "The list was never buried. And your name is on the second page.", "order_in_panel": 1, "position_hint": "bottom_left"},
                    {"segment_type": "caption", "text_content": "[END OF EPISODE 1]", "order_in_panel": 2, "position_hint": "bottom_right"}
                ]
            }
        ]
        return panels


class MockImageProvider(BaseImageProvider):
    def inspect_capabilities(self) -> Dict[str, Any]:
        return {
            "provider_name": "Deterministic Mock Visual Provider (Pillow Engine)",
            "mode": "test_development",
            "is_real_ai": False,
            "supported_aspect_ratios": ["4:5", "3:4", "1:1", "9:16"],
            "supports_inpainting": True,
            "supports_character_sheets": True,
            "cost_per_draft_usd": 0.0,
            "cost_per_final_usd": 0.0,
            "hardware_acceleration": "CPU (Pillow Graphics Synthesizer)"
        }

    def estimate_cost(self, stage: str, count: int = 1) -> float:
        # Mock provider is zero cost
        return 0.0

    def _render_procedural_panel(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        is_final: bool = False,
        aspect_ratio: str = "4:5",
        edit_annotation: Optional[str] = None
    ) -> bytes:
        """
        Renders a rich, art-directed webtoon comic panel using Pillow.
        Includes styling, lighting gradients, character silhouettes, shot markers,
        and clear dev/test mode watermarks.
        """
        # Parse dimensions based on aspect ratio
        width = 800
        height = 1000 if aspect_ratio == "4:5" else (800 if aspect_ratio == "1:1" else 1200)

        img = Image.new("RGB", (width, height), color=(26, 29, 36))
        draw = ImageDraw.Draw(img)

        # 1. Background gradient / mood lighting based on style palette
        palette = style_profile.get("palette_and_colors", ["#1A1D24", "#2E3A4D", "#7B8FA1", "#D97706"])
        if not isinstance(palette, list) or len(palette) < 2:
            palette = ["#1A1D24", "#2E3A4D", "#7B8FA1", "#D97706"]

        # Parse primary and secondary color
        c1 = palette[0] if len(palette) > 0 else "#1A1D24"
        c2 = palette[1] if len(palette) > 1 else "#2E3A4D"

        # Simple vertical gradient fill
        for y in range(height):
            ratio = y / height
            # Interpolate between deep tone and secondary tone
            r = int(26 * (1 - ratio) + 46 * ratio)
            g = int(29 * (1 - ratio) + 58 * ratio)
            b = int(36 * (1 - ratio) + 77 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 2. Lighting ambience overlay (e.g. dramatic spotlight or warm bar)
        local_emotion = panel_spec.get("local_emotion", "Grounded")
        shot_type = panel_spec.get("shot_type", "medium_shot").replace("_", " ").upper()
        cam_angle = panel_spec.get("camera_angle", "eye_level").replace("_", " ").upper()
        panel_num = panel_spec.get("panel_number", 1)

        # Draw aesthetic atmospheric lighting circles/cones
        draw.ellipse([width * 0.2, height * 0.15, width * 0.8, height * 0.75], fill=(35, 45, 62, 120), outline=(60, 80, 110))

        # 3. Dynamic panel border (Thick manhwa style border)
        border_width = 8 if is_final else 4
        border_color = (220, 225, 235) if is_final else (140, 150, 170)
        draw.rectangle([12, 12, width - 12, height - 12], outline=border_color, width=border_width)

        # 4. Draw Character Silhouettes & Composition
        focal_x = width // 2
        focal_y = int(height * 0.55)

        # Head / Body silhouettes
        if "close_up" in shot_type.lower():
            # Close up portrait silhouette
            draw.ellipse([focal_x - 140, focal_y - 220, focal_x + 140, focal_y + 60], fill=(18, 22, 28), outline=(90, 120, 160), width=3)
            # Torso shoulders
            draw.polygon([(focal_x - 220, height - 20), (focal_x - 120, focal_y + 40), (focal_x + 120, focal_y + 40), (focal_x + 220, height - 20)], fill=(15, 18, 24))
            # Hair shape
            draw.arc([focal_x - 150, focal_y - 250, focal_x + 150, focal_y - 50], start=180, end=360, fill=(40, 60, 90), width=6)
        elif "wide" in shot_type.lower():
            # Wide shot full silhouette
            draw.ellipse([focal_x - 40, focal_y - 120, focal_x + 40, focal_y - 40], fill=(15, 18, 24), outline=(80, 100, 130), width=2)
            draw.rectangle([focal_x - 50, focal_y - 40, focal_x + 50, focal_y + 120], fill=(15, 18, 24))
            draw.line([(focal_x - 25, focal_y + 120), (focal_x - 35, focal_y + 240)], fill=(15, 18, 24), width=12)
            draw.line([(focal_x + 25, focal_y + 120), (focal_x + 35, focal_y + 240)], fill=(15, 18, 24), width=12)
        else:
            # Medium shot
            draw.ellipse([focal_x - 90, focal_y - 160, focal_x + 90, focal_y + 20], fill=(18, 22, 28), outline=(90, 120, 160), width=3)
            draw.polygon([(focal_x - 180, height - 30), (focal_x - 80, focal_y), (focal_x + 80, focal_y), (focal_x + 180, height - 30)], fill=(15, 18, 24))

        # 5. Visual Direction & Cinematic Framing Banner
        draw.rectangle([20, 20, width - 20, 75], fill=(10, 14, 20))
        header_text = f"PANEL {panel_num:02d} | {shot_type} [{cam_angle}]"
        draw.text((35, 30), header_text, fill=(240, 245, 255))
        draw.text((35, 52), f"EMOTIONAL DIRECTION: {local_emotion.upper()}", fill=(217, 119, 6))

        # 6. Center Stage Details (Narrative action & character focus)
        action_text = panel_spec.get("character_action", "Action details")
        if len(action_text) > 85:
            action_text = action_text[:85] + "..."
        draw.rectangle([30, height - 140, width - 30, height - 40], fill=(12, 16, 24, 230), outline=(50, 70, 95))
        draw.text((45, height - 130), f"ACTION: {action_text}", fill=(220, 230, 245))
        
        env_text = panel_spec.get("environment_and_background", "Setting details")
        if len(env_text) > 85:
            env_text = env_text[:85] + "..."
        draw.text((45, height - 105), f"ENVIRONMENT: {env_text}", fill=(160, 175, 195))

        focal_text = panel_spec.get("focal_point", "Focal point")
        draw.text((45, height - 80), f"FOCAL POINT: {focal_text}", fill=(130, 190, 255))

        # 7. Edit Annotation if present
        if edit_annotation:
            draw.rectangle([width // 4, height // 2 - 40, width * 3 // 4, height // 2 + 40], fill=(180, 40, 40, 230), outline=(255, 200, 200), width=2)
            draw.text((width // 4 + 20, height // 2 - 15), f"APPLIED TARGETED EDIT:\n{edit_annotation[:45]}", fill=(255, 255, 255))

        # 8. Clear, Non-Negotiable Test/Mock Watermark
        status_tag = "FINAL ART [MOCK AI ENGINE]" if is_final else "ROUGH DRAFT [MOCK AI ENGINE]"
        draw.rectangle([width - 320, height - 36, width - 20, height - 16], fill=(0, 0, 0))
        draw.text((width - 310, height - 33), f"TEST/DEV MODE: {status_tag}", fill=(255, 180, 0))

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def generate_draft(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        raw_bytes = self._render_procedural_panel(
            panel_spec=panel_spec,
            style_profile=style_profile,
            is_final=False,
            aspect_ratio=aspect_ratio
        )
        metadata = {
            "provider": "mock",
            "model_version": "mock-procedural-v1",
            "stage": "draft",
            "is_mock": True,
            "cost_usd": 0.0,
            "duration_seconds": 0.45,
            "prompt_used": f"Webtoon draft shot {panel_spec.get('shot_type')} action: {panel_spec.get('character_action')}",
            "applied_character_ref_count": len(character_refs)
        }
        return raw_bytes, metadata

    async def generate_final(
        self,
        panel_spec: Dict[str, Any],
        style_profile: Dict[str, Any],
        character_refs: List[Dict[str, Any]],
        draft_bytes: Optional[bytes] = None,
        aspect_ratio: str = "4:5"
    ) -> Tuple[bytes, Dict[str, Any]]:
        raw_bytes = self._render_procedural_panel(
            panel_spec=panel_spec,
            style_profile=style_profile,
            is_final=True,
            aspect_ratio=aspect_ratio
        )
        metadata = {
            "provider": "mock",
            "model_version": "mock-procedural-v1",
            "stage": "final",
            "is_mock": True,
            "cost_usd": 0.0,
            "duration_seconds": 0.85,
            "prompt_used": f"High quality finished manhwa panel: {panel_spec.get('narrative_purpose')} with linework {style_profile.get('linework_and_contours')}",
            "applied_character_ref_count": len(character_refs)
        }
        return raw_bytes, metadata

    async def edit_image(
        self,
        base_image_bytes: bytes,
        instruction: str,
        target_region: Optional[str] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        # Load base image and apply targeted edit overlay
        with Image.open(io.BytesIO(base_image_bytes)) as base_img:
            img = base_img.copy()
            draw = ImageDraw.Draw(img)
            # Add targeted correction stamp
            w, h = img.size
            draw.rectangle([50, h // 2 - 50, w - 50, h // 2 + 50], fill=(20, 20, 30, 220), outline=(255, 140, 0), width=3)
            draw.text((70, h // 2 - 25), f"EDITED REGION [{target_region or 'all'}]:\n{instruction}", fill=(255, 230, 150))
            
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            edited_bytes = buf.getvalue()

        metadata = {
            "provider": "mock",
            "model_version": "mock-procedural-v1",
            "stage": "edit",
            "is_mock": True,
            "cost_usd": 0.0,
            "duration_seconds": 0.35,
            "instruction": instruction,
            "target_region": target_region
        }
        return edited_bytes, metadata

mock_llm_provider = MockLLMProvider()
mock_image_provider = MockImageProvider()
