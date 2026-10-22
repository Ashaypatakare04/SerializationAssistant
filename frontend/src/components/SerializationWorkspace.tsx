"use client";

import React, { useState } from "react";
import { Project, AdaptationPlan, Episode } from "../types";
import { api } from "../lib/api";
import {
  Film,
  Sparkles,
  CheckCircle,
  Activity,
  ArrowRight,
  Target,
  Layers,
  ChevronRight
} from "lucide-react";

interface SerializationWorkspaceProps {
  project: Project;
  adaptationPlans: AdaptationPlan[];
  selectedEpisode: Episode | null;
  onSelectEpisode: (ep: Episode) => void;
  onRefresh: () => Promise<void>;
  onProceedToStoryboard: () => void;
}

export const SerializationWorkspace: React.FC<SerializationWorkspaceProps> = ({
  project,
  adaptationPlans,
  selectedEpisode,
  onSelectEpisode,
  onRefresh,
  onProceedToStoryboard,
}) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const activePlan = adaptationPlans[0];

  const handleGeneratePlan = async () => {
    setIsGenerating(true);
    setMessage(null);
    try {
      const job = await api.triggerAdaptationPlan(project.id);
      await api.pollJob(job.id);
      setMessage({ type: "success", text: "Adaptation Plan and Scene/Beat emotional progressions generated!" });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to generate adaptation plan." });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleApprovePlan = async () => {
    if (!activePlan) return;
    setIsApproving(true);
    try {
      await api.recordApproval({
        artifact_type: "adaptation_plan",
        artifact_id: activePlan.id,
        artifact_version: activePlan.version,
        approved_by: "creator",
        comments: "Serialization structure, pacing, and beat-level emotional direction approved."
      });
      setMessage({ type: "success", text: "Adaptation Plan approved! Gate cleared to generate storyboard." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Approval failed." });
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Film className="w-5 h-5 text-studio-accent" />
            <span>Serialization & Creative Direction</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Progressive planning: Arcs, episodes, scenes, and beat-level emotional progressions without visual style drift.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleGeneratePlan}
            disabled={isGenerating}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-200 transition disabled:opacity-50"
          >
            <Sparkles className="w-4 h-4 text-studio-cyan" />
            <span>{isGenerating ? "Planning..." : "Propose Adaptation Plan"}</span>
          </button>

          {activePlan && (
            <button
              onClick={handleApprovePlan}
              disabled={isApproving || activePlan.is_approved}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
                activePlan.is_approved
                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800 cursor-default"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg"
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              <span>{activePlan.is_approved ? "Plan Approved (Gate Cleared)" : "Approve Adaptation Plan"}</span>
            </button>
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

      {!activePlan ? (
        <div className="border border-dashed border-studio-700 rounded-xl p-12 text-center bg-studio-850/40">
          <Film className="w-12 h-12 text-studio-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-studio-200">No Adaptation Plan Proposed</h3>
          <p className="text-xs text-studio-400 max-w-sm mx-auto mt-1 mb-4">
            Click &quot;Propose Adaptation Plan&quot; to generate an episode breakdown, scene pacing, and beat-level emotional directions.
          </p>
          <button
            onClick={handleGeneratePlan}
            disabled={isGenerating}
            className="px-4 py-2 bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white rounded-lg transition"
          >
            Generate Plan Now
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Plan Meta Card */}
          <div className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <span className="font-bold text-white text-base">{activePlan.title}</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-studio-800 text-studio-accent border border-studio-700">
                  Version {activePlan.version}
                </span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                  activePlan.is_approved ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-amber-950 text-amber-400 border border-amber-800"
                }`}>
                  {activePlan.is_approved ? "APPROVED" : "DRAFT"}
                </span>
              </div>
              <p className="text-xs text-studio-400">
                Pacing: <span className="text-studio-200 font-medium">{activePlan.pacing_strategy}</span> • Based on Story Bible v{activePlan.story_bible_version}
              </p>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-xs text-studio-400 font-medium">
                {activePlan.episodes?.length || 0} Episode(s) Planned
              </span>
            </div>
          </div>

          {/* Episodes & Scene/Beat Breakdown */}
          <div className="space-y-6">
            {activePlan.episodes?.map((ep) => (
              <div key={ep.id} className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-studio-800 mb-4">
                  <div>
                    <h3 className="text-base font-bold text-white flex items-center space-x-2">
                      <span className="text-studio-accent font-mono text-sm">EP {String(ep.episode_number).padStart(2, "0")}</span>
                      <span>{ep.title}</span>
                    </h3>
                    <p className="text-xs text-studio-400 mt-0.5">{ep.premise_and_purpose}</p>
                  </div>

                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-studio-400">
                      Target: <span className="text-studio-cyan font-bold">{ep.target_panel_count} Panels</span>
                    </span>

                    <button
                      onClick={() => {
                        onSelectEpisode(ep);
                        onProceedToStoryboard();
                      }}
                      className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow"
                    >
                      <Layers className="w-3.5 h-3.5" />
                      <span>Edit Storyboard</span>
                    </button>
                  </div>
                </div>

                {/* Narrative Hooks */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4 text-xs">
                  <div className="p-2.5 rounded bg-studio-900 border border-studio-800">
                    <span className="text-studio-cyan font-bold block mb-0.5">Opening Hook:</span>
                    <p className="text-studio-300">{ep.opening_hook}</p>
                  </div>
                  <div className="p-2.5 rounded bg-studio-900 border border-studio-800">
                    <span className="text-studio-rose font-bold block mb-0.5">Ending Cliffhanger Beat:</span>
                    <p className="text-studio-300">{ep.ending_cliffhanger_or_beat}</p>
                  </div>
                </div>

                {/* Scenes and Beat-Level Emotional Progression */}
                <div className="space-y-3">
                  <div className="text-xs font-bold text-studio-400 uppercase tracking-wider">
                    Scene Breakdowns & Emotional Trajectories:
                  </div>

                  {ep.scenes?.map((scene) => (
                    <div key={scene.id} className="p-4 rounded-xl bg-studio-900 border border-studio-800 space-y-3">
                      <div className="flex items-center justify-between pb-2 border-b border-studio-800/80">
                        <div>
                          <span className="font-bold text-white text-xs">
                            Scene {scene.scene_number}: {scene.title}
                          </span>
                          <span className="text-[11px] text-studio-400 ml-2">({scene.environment} • {scene.time_of_day})</span>
                        </div>
                        <span className="text-[10px] text-studio-500 uppercase">{scene.pacing_note} pacing</span>
                      </div>

                      {/* Beats Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {scene.beats?.map((beat) => (
                          <div key={beat.id} className="p-3 rounded-lg bg-studio-850 border border-studio-750 text-xs space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-studio-accent text-[11px]">
                                Beat {beat.beat_number}
                              </span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-studio-800 text-studio-cyan border border-studio-700">
                                Intensity: {beat.emotional_intensity}/10
                              </span>
                            </div>

                            <div>
                              <span className="text-studio-500 font-semibold block text-[10px]">EMOTIONS:</span>
                              <span className="text-white font-medium">{beat.dominant_emotion}</span>
                              {beat.secondary_emotion && (
                                <span className="text-studio-400"> (Sec: {beat.secondary_emotion})</span>
                              )}
                            </div>

                            <div>
                              <span className="text-studio-500 font-semibold block text-[10px]">PROGRESSION:</span>
                              <p className="text-studio-300 italic text-[11px]">{beat.emotional_progression}</p>
                            </div>

                            <div>
                              <span className="text-studio-500 font-semibold block text-[10px]">ACTION:</span>
                              <p className="text-studio-200">{beat.narrative_action}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
