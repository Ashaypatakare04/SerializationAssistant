"use client";

import React, { useState } from "react";
import { Episode, Panel } from "../types";
import { api } from "../lib/api";
import {
  Layers,
  Sparkles,
  CheckCircle,
  Camera,
  MessageSquare,
  Volume2,
  Smile,
  Edit2,
  Save,
  Play,
  ArrowRight
} from "lucide-react";

interface StoryboardEditorProps {
  episode: Episode | null;
  onRefresh: () => Promise<void>;
  onProceedToReview: () => void;
}

export const StoryboardEditor: React.FC<StoryboardEditorProps> = ({
  episode,
  onRefresh,
  onProceedToReview,
}) => {
  const [editingPanelId, setEditingPanelId] = useState<string | null>(null);
  const [editShotType, setEditShotType] = useState("");
  const [editCameraAngle, setEditCameraAngle] = useState("");
  const [editAction, setEditAction] = useState("");
  const [editFocalPoint, setEditFocalPoint] = useState("");
  const [editEmotion, setEditEmotion] = useState("");
  const [isGeneratingStoryboard, setIsGeneratingStoryboard] = useState(false);
  const [generatingDraftPanelId, setGeneratingDraftPanelId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  if (!episode) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-4 text-center">
        <Layers className="w-12 h-12 text-studio-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-studio-200">No Episode Selected</h3>
        <p className="text-xs text-studio-400 mt-1">
          Please select an episode from the Serialization Planning stage first.
        </p>
      </div>
    );
  }

  const allPanels: Panel[] = [];
  episode.scenes?.forEach((s) => {
    s.beats?.forEach((b) => {
      allPanels.push(...b.panels);
    });
  });
  allPanels.sort((a, b) => a.panel_number - b.panel_number);

  const handleGenerateStoryboard = async () => {
    setIsGeneratingStoryboard(true);
    setMessage(null);
    try {
      const job = await api.triggerStoryboard(episode.id);
      await api.pollJob(job.id);
      setMessage({ type: "success", text: "Structured webtoon storyboard panels and dialogues generated!" });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to generate storyboard." });
    } finally {
      setIsGeneratingStoryboard(false);
    }
  };

  const handleStartEdit = (p: Panel) => {
    setEditingPanelId(p.id);
    setEditShotType(p.shot_type);
    setEditCameraAngle(p.camera_angle);
    setEditAction(p.character_action);
    setEditFocalPoint(p.focal_point);
    setEditEmotion(p.local_emotion);
  };

  const handleSaveEdit = async (panelId: string) => {
    try {
      await api.updatePanel(panelId, {
        shot_type: editShotType,
        camera_angle: editCameraAngle,
        character_action: editAction,
        focal_point: editFocalPoint,
        local_emotion: editEmotion,
      });
      setEditingPanelId(null);
      setMessage({ type: "success", text: "Panel specifications updated. Version incremented and re-review required." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to update panel." });
    }
  };

  const handleApprovePanel = async (panel: Panel) => {
    try {
      await api.recordApproval({
        artifact_type: "panel",
        artifact_id: panel.id,
        artifact_version: panel.version,
        approved_by: "creator",
        comments: "Storyboard panel approved by creator."
      });
      setMessage({ type: "success", text: `Panel ${panel.panel_number} approved! Final illustration can now be generated.` });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to approve panel." });
    }
  };

  const handleGenerateDraft = async (panelId: string) => {
    setGeneratingDraftPanelId(panelId);
    setMessage(null);
    try {
      const job = await api.triggerPanelGeneration(panelId, "draft");
      await api.pollJob(job.id);
      setMessage({ type: "success", text: "Draft artwork thumbnail generated successfully!" });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Draft generation failed." });
    } finally {
      setGeneratingDraftPanelId(null);
    }
  };

  const handleGenerateAllDrafts = async () => {
    setMessage(null);
    try {
      for (const p of allPanels) {
        const job = await api.triggerPanelGeneration(p.id, "draft");
        await api.pollJob(job.id);
      }
      setMessage({ type: "success", text: "All draft illustrations generated successfully!" });
      await onRefresh();
      onProceedToReview();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Batch draft generation encountered an issue." });
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Layers className="w-5 h-5 text-studio-accent" />
            <span>Storyboard Editor: {episode.title}</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Sequential panel cards with camera framing, local emotional direction, actions, dialogue lettering, and human approval gates.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {allPanels.length === 0 ? (
            <button
              onClick={handleGenerateStoryboard}
              disabled={isGeneratingStoryboard}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isGeneratingStoryboard ? "Building Storyboard..." : "Generate Storyboard"}</span>
            </button>
          ) : (
            <>
              <button
                onClick={handleGenerateAllDrafts}
                className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-200 transition"
              >
                <Play className="w-3.5 h-3.5 text-studio-cyan" />
                <span>Generate All Drafts</span>
              </button>

              <button
                onClick={onProceedToReview}
                className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow"
              >
                <span>Illustration Review</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {message && (
        <div
          className={`p-3 rounded-lg text-xs font-medium mb-5 border ${
            message.type === "success"
              ? "bg-emerald-950/40 border-emerald-700 text-emerald-300"
              : "bg-rose-950/40 border-rose-700 text-rose-300"
          }`}
        >
          {message.text}
        </div>
      )}

      {/* Panels List */}
      {allPanels.length === 0 ? (
        <div className="border border-dashed border-studio-700 rounded-xl p-12 text-center bg-studio-850/40">
          <Layers className="w-12 h-12 text-studio-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-studio-200">No Storyboard Panels Yet</h3>
          <p className="text-xs text-studio-400 max-w-sm mx-auto mt-1 mb-4">
            Click &quot;Generate Storyboard&quot; to transform this episode&apos;s scenes and beats into sequential webtoon panel specifications.
          </p>
          <button
            onClick={handleGenerateStoryboard}
            disabled={isGeneratingStoryboard}
            className="px-4 py-2 bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white rounded-lg transition"
          >
            Generate Storyboard Now
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {allPanels.map((panel) => {
            const isEditing = editingPanelId === panel.id;
            return (
              <div
                key={panel.id}
                className={`bg-studio-850 border rounded-xl p-5 shadow transition ${
                  panel.is_approved ? "border-emerald-800/80" : "border-studio-750"
                }`}
              >
                {/* Panel Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-studio-800 mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="w-8 h-8 rounded-lg bg-studio-900 border border-studio-700 font-mono font-bold text-sm text-studio-accent flex items-center justify-center">
                      #{panel.panel_number}
                    </span>
                    <div>
                      <span className="font-bold text-white text-sm">
                        Panel {panel.panel_number} • {panel.narrative_purpose}
                      </span>
                      <span className="text-xs text-studio-500 block">Version {panel.version}</span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleApprovePanel(panel)}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                        panel.is_approved
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-studio-750 hover:bg-emerald-900 hover:text-emerald-300 text-studio-300"
                      }`}
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>{panel.is_approved ? "Panel Approved" : "Approve Panel"}</span>
                    </button>

                    <button
                      onClick={() => handleGenerateDraft(panel.id)}
                      disabled={generatingDraftPanelId === panel.id}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-cyan disabled:opacity-50"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{generatingDraftPanelId === panel.id ? "Drafting..." : "Draft Art"}</span>
                    </button>

                    {!isEditing ? (
                      <button
                        onClick={() => handleStartEdit(panel)}
                        className="p-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 text-studio-400 hover:text-white"
                        title="Edit specifications"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleSaveEdit(panel.id)}
                        className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white"
                      >
                        <Save className="w-3.5 h-3.5" />
                        <span>Save</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Panel Specs & Dialogue */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  {/* Visual Framing */}
                  <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg space-y-2">
                    <span className="font-bold text-studio-cyan flex items-center space-x-1">
                      <Camera className="w-3.5 h-3.5" />
                      <span>Camera & Composition</span>
                    </span>

                    {isEditing ? (
                      <div className="space-y-1.5">
                        <select
                          value={editShotType}
                          onChange={(e) => setEditShotType(e.target.value)}
                          className="w-full px-2 py-1 bg-studio-850 border border-studio-700 rounded text-xs text-white"
                        >
                          <option value="extreme_close_up">Extreme Close-Up</option>
                          <option value="close_up">Close-Up</option>
                          <option value="medium_shot">Medium Shot</option>
                          <option value="full_shot">Full Shot</option>
                          <option value="wide_shot">Wide Shot</option>
                        </select>
                        <select
                          value={editCameraAngle}
                          onChange={(e) => setEditCameraAngle(e.target.value)}
                          className="w-full px-2 py-1 bg-studio-850 border border-studio-700 rounded text-xs text-white"
                        >
                          <option value="eye_level">Eye Level</option>
                          <option value="low_angle">Low Angle</option>
                          <option value="high_angle">High Angle</option>
                          <option value="dutch_angle">Dutch Angle (Tilted)</option>
                        </select>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div>
                          <span className="text-studio-500 font-semibold">Shot:</span>{" "}
                          <span className="text-studio-200 capitalize">{panel.shot_type.replace("_", " ")}</span>
                        </div>
                        <div>
                          <span className="text-studio-500 font-semibold">Angle:</span>{" "}
                          <span className="text-studio-200 capitalize">{panel.camera_angle.replace("_", " ")}</span>
                        </div>
                        <div>
                          <span className="text-studio-500 font-semibold">Ratio:</span>{" "}
                          <span className="text-studio-200">{panel.aspect_ratio}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Action & Emotion */}
                  <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg space-y-2">
                    <span className="font-bold text-studio-accent flex items-center space-x-1">
                      <Smile className="w-3.5 h-3.5" />
                      <span>Action & Direction</span>
                    </span>

                    {isEditing ? (
                      <div className="space-y-1.5">
                        <input
                          type="text"
                          value={editAction}
                          onChange={(e) => setEditAction(e.target.value)}
                          placeholder="Character action"
                          className="w-full px-2 py-1 bg-studio-850 border border-studio-700 rounded text-xs text-white"
                        />
                        <input
                          type="text"
                          value={editFocalPoint}
                          onChange={(e) => setEditFocalPoint(e.target.value)}
                          placeholder="Focal point"
                          className="w-full px-2 py-1 bg-studio-850 border border-studio-700 rounded text-xs text-white"
                        />
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <div>
                          <span className="text-studio-500 font-semibold">Action:</span>{" "}
                          <span className="text-studio-200">{panel.character_action}</span>
                        </div>
                        <div>
                          <span className="text-studio-500 font-semibold">Focal Point:</span>{" "}
                          <span className="text-studio-200">{panel.focal_point}</span>
                        </div>
                        <div>
                          <span className="text-studio-500 font-semibold">Local Emotion:</span>{" "}
                          <span className="text-studio-accent font-medium">{panel.local_emotion}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Dialogue & Lettering Layer */}
                  <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg space-y-2">
                    <span className="font-bold text-studio-rose flex items-center space-x-1">
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>Dialogue & Sound Effects ({panel.dialogues?.length || 0})</span>
                    </span>

                    <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
                      {panel.dialogues?.map((d) => (
                        <div key={d.id} className="p-1.5 rounded bg-studio-850 border border-studio-750">
                          <span className="text-[10px] font-bold text-studio-cyan uppercase block">
                            [{d.segment_type.replace("_", " ")}] {d.speaker_name && `• ${d.speaker_name}`}
                          </span>
                          <span className="text-studio-200 italic">&ldquo;{d.text_content}&rdquo;</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
