"use client";

import React, { useState, useEffect } from "react";
import { Episode, Panel, Asset, AssetVersion } from "../types";
import { api, getStorageUrl } from "../lib/api";
import {
  Sparkles,
  CheckCircle,
  RefreshCw,
  Wand2,
  AlertCircle,
  Sliders,
  DollarSign,
  Clock,
  Layers,
  ArrowRight,
  ShieldAlert
} from "lucide-react";

interface IllustrationReviewProps {
  episode: Episode | null;
  onRefresh: () => Promise<void>;
  onProceedToReader: () => void;
}

export const IllustrationReview: React.FC<IllustrationReviewProps> = ({
  episode,
  onRefresh,
  onProceedToReader,
}) => {
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null);
  const [panelAssets, setPanelAssets] = useState<Asset[]>([]);
  const [editInstruction, setEditInstruction] = useState("");
  const [targetRegion, setTargetRegion] = useState("face");
  const [isProcessing, setIsProcessing] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const allPanels: Panel[] = [];
  episode?.scenes?.forEach((s) => {
    s.beats?.forEach((b) => {
      allPanels.push(...b.panels);
    });
  });
  allPanels.sort((a, b) => a.panel_number - b.panel_number);

  useEffect(() => {
    if (allPanels.length > 0 && !selectedPanel) {
      setSelectedPanel(allPanels[0]);
    }
  }, [allPanels, selectedPanel]);

  useEffect(() => {
    if (selectedPanel) {
      api.getPanelAssets(selectedPanel.id).then((assets) => {
        setPanelAssets(assets);
      }).catch(() => {
        setPanelAssets([]);
      });
    }
  }, [selectedPanel]);

  if (!episode || allPanels.length === 0) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-4 text-center">
        <Sparkles className="w-12 h-12 text-studio-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-studio-200">No Storyboard Panels Found</h3>
        <p className="text-xs text-studio-400 mt-1">
          Please create and approve storyboard panels before reviewing illustrations.
        </p>
      </div>
    );
  }

  const activeAsset = panelAssets[0];
  const activeVersion = activeAsset?.versions?.[activeAsset.versions.length - 1];

  const handleGenerateFinal = async () => {
    if (!selectedPanel) return;
    if (!selectedPanel.is_approved) {
      setMessage({
        type: "error",
        text: "Approval Gate Warning: Panel must be approved in Storyboard before generating final illustration."
      });
      return;
    }

    setIsProcessing(true);
    setMessage(null);
    try {
      const job = await api.triggerPanelGeneration(selectedPanel.id, "final");
      await api.pollJob(job.id);
      setMessage({ type: "success", text: `Final artwork generated for Panel ${selectedPanel.panel_number}!` });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Final generation failed." });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyEdit = async () => {
    if (!activeAsset || !editInstruction.trim()) return;
    setIsProcessing(true);
    setMessage(null);
    try {
      const job = await api.triggerAssetEdit(activeAsset.id, {
        instruction: editInstruction,
        target_region: targetRegion
      });
      await api.pollJob(job.id);
      setEditInstruction("");
      setMessage({ type: "success", text: `Targeted correction applied to [${targetRegion}]!` });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel!.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Edit failed." });
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApproveAssetVersion = async () => {
    if (!activeVersion) return;
    setIsProcessing(true);
    try {
      await api.recordApproval({
        artifact_type: "asset_version",
        artifact_id: activeVersion.id,
        artifact_version: activeVersion.version_number,
        approved_by: "creator",
        comments: "Illustration accepted for final episode webtoon publication."
      });
      setMessage({ type: "success", text: `Illustration version ${activeVersion.version_number} approved!` });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel!.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Approval failed." });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-studio-accent" />
            <span>Illustration Review & Correction Studio</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Inspect draft and final illustrations against visual references, request targeted corrections, and approve finished artwork.
          </p>
        </div>

        <button
          onClick={onProceedToReader}
          className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow"
        >
          <span>Preview Webtoon Strip</span>
          <ArrowRight className="w-4 h-4" />
        </button>
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

      {/* Main Review Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Panel Selector Strip */}
        <div className="lg:col-span-1 space-y-2">
          <h3 className="text-xs font-bold text-studio-400 uppercase tracking-wider mb-2">
            Episode Panels ({allPanels.length})
          </h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {allPanels.map((p) => {
              const isSelected = selectedPanel?.id === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPanel(p)}
                  className={`p-3 rounded-xl cursor-pointer border transition text-xs flex items-center justify-between ${
                    isSelected
                      ? "bg-studio-800 border-studio-accent shadow-md"
                      : "bg-studio-850 border-studio-750 hover:border-studio-600"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6 rounded bg-studio-900 text-studio-accent font-mono font-bold flex items-center justify-center text-[11px]">
                      #{p.panel_number}
                    </span>
                    <div>
                      <span className="font-semibold text-white block capitalize">
                        {p.shot_type.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-studio-400 truncate max-w-[120px] block">
                        {p.local_emotion}
                      </span>
                    </div>
                  </div>

                  {p.is_approved ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <span className="text-[10px] text-amber-400 font-semibold uppercase">Pending</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Center: Selected Panel High-Res Artwork Viewer */}
        <div className="lg:col-span-2 space-y-4">
          {selectedPanel && (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
              <div className="flex items-center justify-between pb-3 border-b border-studio-800 mb-4">
                <div>
                  <h3 className="font-bold text-white text-base">
                    Panel #{selectedPanel.panel_number}: {selectedPanel.shot_type.replace("_", " ").toUpperCase()}
                  </h3>
                  <span className="text-xs text-studio-400">
                    Emotion: <span className="text-studio-accent font-medium">{selectedPanel.local_emotion}</span>
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleGenerateFinal}
                    disabled={isProcessing}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{isProcessing ? "Rendering..." : "Generate Final Art"}</span>
                  </button>

                  {activeVersion && (
                    <button
                      onClick={handleApproveAssetVersion}
                      disabled={isProcessing || activeVersion.is_approved}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                        activeVersion.is_approved
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-emerald-600 hover:bg-emerald-500 text-white"
                      }`}
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>{activeVersion.is_approved ? "Art Approved" : "Approve Art"}</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Artwork Viewport */}
              <div className="relative aspect-[4/5] bg-studio-950 rounded-xl overflow-hidden border border-studio-800 flex items-center justify-center">
                {activeVersion ? (
                  /* eslint-disable-next-line @next/next/no-img-element */
                  <img
                    src={getStorageUrl(activeVersion.storage_key)}
                    alt={`Panel ${selectedPanel.panel_number}`}
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-center p-6 text-studio-500">
                    <Sparkles className="w-10 h-10 mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No artwork generated yet for this panel.</p>
                    <p className="text-[11px] text-studio-600 mt-1">
                      Click &quot;Generate Final Art&quot; or draft in Storyboard.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Targeted Editing & Provenance Metadata */}
        <div className="lg:col-span-1 space-y-4">
          {/* Targeted Inpainting / Correction */}
          <div className="bg-studio-850 border border-studio-750 rounded-xl p-4 shadow space-y-3">
            <h4 className="text-xs font-bold text-white flex items-center space-x-1.5">
              <Wand2 className="w-3.5 h-3.5 text-studio-accent" />
              <span>Targeted Correction</span>
            </h4>
            <p className="text-[11px] text-studio-400">
              Apply localized corrections without discarding the entire panel composition.
            </p>

            <div>
              <label className="block text-[10px] font-semibold text-studio-400 mb-1">Target Region</label>
              <select
                value={targetRegion}
                onChange={(e) => setTargetRegion(e.target.value)}
                className="w-full px-2 py-1.5 bg-studio-900 border border-studio-700 rounded text-xs text-white"
              >
                <option value="face">Facial Expression & Eyes</option>
                <option value="hair">Hair Rendering</option>
                <option value="clothing">Clothing & Folds</option>
                <option value="lighting">Rim Lighting / Shadows</option>
                <option value="background">Background Perspective</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-studio-400 mb-1">Correction Prompt</label>
              <textarea
                rows={3}
                value={editInstruction}
                onChange={(e) => setEditInstruction(e.target.value)}
                placeholder="e.g. Sharpen eye highlights and deepen shadow..."
                className="w-full px-2 py-1.5 bg-studio-900 border border-studio-700 rounded text-xs text-white"
              />
            </div>

            <button
              onClick={handleApplyEdit}
              disabled={isProcessing || !activeAsset || !editInstruction.trim()}
              className="w-full py-1.5 bg-studio-750 hover:bg-studio-700 text-xs font-semibold text-white rounded transition disabled:opacity-50"
            >
              {isProcessing ? "Correcting..." : "Apply Edit"}
            </button>
          </div>

          {/* Provenance & Cost Metadata */}
          {activeVersion && (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-4 shadow text-xs space-y-2">
              <h4 className="text-[11px] font-bold text-studio-300 uppercase tracking-wider">
                Provenance & Audit
              </h4>
              <div className="space-y-1 text-studio-400">
                <div>
                  <span className="font-semibold text-studio-500">Stage:</span>{" "}
                  <span className="text-white uppercase font-bold text-[10px]">{activeVersion.stage}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Provider:</span>{" "}
                  <span className="text-studio-200">{activeVersion.provider}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Duration:</span>{" "}
                  <span className="text-studio-200">{activeVersion.duration_seconds}s</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Est. Cost:</span>{" "}
                  <span className="text-studio-emerald font-mono">${activeVersion.estimated_cost_usd.toFixed(3)}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Version:</span>{" "}
                  <span className="text-studio-cyan font-mono">v{activeVersion.version_number}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
