export interface SourceSection {
  id: string;
  section_index: number;
  title: string;
  content: string;
  start_char: number;
  end_char: number;
}

export interface SourceDocument {
  id: string;
  project_id: string;
  filename: string;
  mime_type: string;
  extraction_status: string;
  char_count: number;
  word_count: number;
  created_at: string;
  sections: SourceSection[];
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  target_format: string;
  current_stage: string;
  status: string;
  owner_id: string;
  configuration: Record<string, any>;
  created_at: string;
  updated_at: string;
  documents: SourceDocument[];
}

export interface CharacterVersion {
  id: string;
  character_id: string;
  version_number: number;
  label: string;
  physical_appearance: string;
  hair_style_and_color: string;
  clothing_and_accessories: string;
  distinctive_features: string;
  body_proportions: string;
  story_context: string;
  is_approved: boolean;
}

export interface Character {
  id: string;
  story_bible_id: string;
  canonical_name: string;
  aliases: string[];
  role: string;
  personality_summary: string;
  voice_and_mannerisms: string;
  active_version_id?: string;
  versions: CharacterVersion[];
}

export interface StoryEvent {
  id: string;
  chronological_order: number;
  title: string;
  summary: string;
  source_locator?: string;
  emotional_weight: string;
}

export interface ContinuityFact {
  id: string;
  category: string;
  statement: string;
  source_locator?: string;
  is_confirmed: boolean;
}

export interface Relationship {
  id: string;
  source_character_id: string;
  target_character_id: string;
  relationship_type: string;
  dynamics_description: string;
}

export interface StoryBible {
  id: string;
  project_id: string;
  version: number;
  premise: string;
  genre: string;
  target_audience?: string;
  narrative_tone: string;
  world_rules: any[];
  themes: any[];
  status: string;
  uncertainties: any[];
  created_at: string;
  characters: Character[];
  events: StoryEvent[];
  continuity_facts: ContinuityFact[];
  relationships: Relationship[];
}

export interface ReferenceAsset {
  id: string;
  project_id: string;
  filename: string;
  storage_key: string;
  role: "visual_style" | "character_identity" | "layout_composition" | "environment";
  label: string;
  description?: string;
  width: number;
  height: number;
  mime_type: string;
  is_active: boolean;
  created_at: string;
}

export interface StyleProfileVersion {
  id: string;
  style_profile_id: string;
  version_number: number;
  linework_and_contours: string;
  anatomy_and_proportions: string;
  facial_features_and_expressions: string;
  palette_and_colors: string[];
  color_relationships: string;
  shading_and_lighting: string;
  texture_and_rendering: string;
  background_treatment: string;
  composition_conventions: string;
  degree_of_stylization: string;
  reference_isolation_notes: string;
  uncertainties: any[];
  reference_asset_ids: string[];
  is_approved: boolean;
  approved_by?: string;
  created_at: string;
}

export interface StyleProfile {
  id: string;
  project_id: string;
  current_version: number;
  status: string;
  versions: StyleProfileVersion[];
}

export interface DialogueSegment {
  id: string;
  panel_id: string;
  segment_type: "speech_bubble" | "caption" | "sound_effect" | "thought_bubble";
  speaker_character_id?: string;
  speaker_name: string;
  text_content: string;
  order_in_panel: number;
  position_hint: string;
}

export interface Panel {
  id: string;
  beat_id: string;
  panel_number: number;
  narrative_purpose: string;
  source_locator?: string;
  character_ids: string[];
  character_appearance_versions: Record<string, number>;
  shot_type: string;
  camera_angle: string;
  composition_notes: string;
  focal_point: string;
  aspect_ratio: string;
  character_action: string;
  expression_and_body_language: string;
  environment_and_background: string;
  lighting_direction: string;
  local_emotion: string;
  vertical_spacing_after_px: number;
  version: number;
  is_approved: boolean;
  approved_by?: string;
  active_asset_id?: string;
  dialogues: DialogueSegment[];
}

export interface Beat {
  id: string;
  scene_id: string;
  beat_number: number;
  dominant_emotion: string;
  secondary_emotion?: string;
  emotional_intensity: number;
  emotional_progression: string;
  narrative_action: string;
  visual_exaggeration_constraint: string;
  panels: Panel[];
}

export interface Scene {
  id: string;
  episode_id: string;
  scene_number: number;
  title: string;
  narrative_purpose: string;
  environment: string;
  time_of_day: string;
  pacing_note: string;
  beats: Beat[];
}

export interface Episode {
  id: string;
  adaptation_plan_id: string;
  episode_number: number;
  title: string;
  premise_and_purpose: string;
  source_sections_covered: string[];
  opening_hook: string;
  ending_cliffhanger_or_beat: string;
  target_panel_count: number;
  status: string;
  scenes: Scene[];
}

export interface AdaptationPlan {
  id: string;
  project_id: string;
  version: number;
  title: string;
  target_episodes_estimate: number;
  pacing_strategy: string;
  story_bible_version: number;
  status: string;
  is_approved: boolean;
  approved_by?: string;
  episodes: Episode[];
}

export interface AssetVersion {
  id: string;
  asset_id: string;
  version_number: number;
  storage_key: string;
  thumbnail_key?: string;
  stage: "draft" | "final" | "edit";
  provider: string;
  model_version: string;
  prompt_used: string;
  style_profile_version: number;
  character_reference_ids: string[];
  estimated_cost_usd: number;
  actual_cost_usd: number;
  duration_seconds: number;
  is_approved: boolean;
  is_mock: boolean;
  created_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  panel_id?: string;
  asset_type: string;
  current_version: number;
  status: string;
  versions: AssetVersion[];
}

export interface Job {
  id: string;
  project_id: string;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress_percentage: number;
  stage_description: string;
  payload: Record<string, any>;
  result_data: Record<string, any>;
  error_message?: string;
  retry_count: number;
  created_at: string;
}

export interface QAFinding {
  category: "narrative" | "visual" | "sequence";
  severity: "info" | "warning" | "error";
  title: string;
  description: string;
  target_id?: string;
  target_type?: string;
  suggestion?: string;
}

export interface FullQAReport {
  overall_status: "passed" | "review_required" | "blocked";
  narrative: {
    passed: boolean;
    score: number;
    total_checks: number;
    findings: QAFinding[];
  };
  visual: {
    passed: boolean;
    score: number;
    style_fidelity_score: number;
    character_consistency_score: number;
    findings: QAFinding[];
  };
  sequence: {
    passed: boolean;
    score: number;
    pacing_score: number;
    reading_flow_score: number;
    findings: QAFinding[];
  };
}
