"use client";

import React, { useState } from "react";
import { Project, ReferenceAsset, StyleProfile } from "../types";
import { api, getStorageUrl } from "../lib/api";
import {
  Palette,
  UploadCloud,
  Sparkles,
  CheckCircle,
  Eye,
  Sliders,
  Shield,
  Layers,
  Image as ImageIcon,
  Edit3
} from "lucide-react";

interface ReferenceStyleWorkspaceProps {
  project: Project;
  references: ReferenceAsset[];
  styleProfile: StyleProfile | null;
  onRefresh: () => Promise<void>;
}

export const ReferenceStyleWorkspace: React.FC<ReferenceStyleWorkspaceProps> = ({
  project,
  references,
  styleProfile,
  onRefresh,
}) => {
  const [role, setRole] = useState<"visual_style" | "character_identity" | "layout_composition" | "environment">("visual_style");
  const [label, setLabel] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const activeVersion = styleProfile?.versions?.[styleProfile.versions.length - 1];

  const handleUploadImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("role", role);
      formData.append("label", label || file.name);
      await api.uploadReference(project.id, formData);
      setLabel("");
      setMessage({ type: "success", text: `Reference '${file.name}' uploaded under role '${role}'.` });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to upload reference image." });
    } finally {
      setIsUploading(false);
    }
  };

  const handleRunStyleAnalysis = async () => {
    setIsAnalyzing(true);
    setMessage(null);
    try {
      const job = await api.triggerStyleAnalysis(project.id);
      await api.pollJob(job.id);
      setMessage({ type: "success", text: "Visual Style Profile extracted from references successfully!" });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Style analysis failed." });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApproveStyle = async () => {
    if (!styleProfile || !activeVersion) return;
    setIsApproving(true);
    try {
      await api.recordApproval({
        artifact_type: "style_profile",
        artifact_id: styleProfile.id,
        artifact_version: activeVersion.version_number,
        approved_by: "creator",
        comments: "Visual style profile approved for webtoon generation."
      });
      setMessage({ type: "success", text: "Style Profile approved! Downstream illustration runs will use this profile." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Approval failed." });
    } finally {
      setIsApproving(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Palette className="w-5 h-5 text-studio-accent" />
            <span>Visual References & Style Profile</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Manage artistic references (style, character sheets, layout) and establish a versioned, art-directed style profile.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {references.length > 0 && (
            <button
              onClick={handleRunStyleAnalysis}
              disabled={isAnalyzing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-200 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-studio-accent" />
              <span>{isAnalyzing ? "Analyzing References..." : "Extract Style Profile"}</span>
            </button>
          )}

          {activeVersion && (
            <button
              onClick={handleApproveStyle}
              disabled={isApproving || activeVersion.is_approved}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
                activeVersion.is_approved
                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800 cursor-default"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg"
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              <span>{activeVersion.is_approved ? "Style Profile Approved" : "Approve Style Profile"}</span>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Reference Upload & Gallery */}
        <div className="lg:col-span-1 space-y-5">
          <div className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
            <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
              <UploadCloud className="w-4 h-4 text-studio-accent" />
              <span>Upload Visual Reference</span>
            </h3>

            <div className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-studio-400 mb-1">
                  Reference Role *
                </label>
                <select
                  value={role}
                  onChange={(e: any) => setRole(e.target.value)}
                  className="w-full px-3 py-1.5 bg-studio-900 border border-studio-700 rounded-lg text-xs text-white focus:outline-none focus:border-studio-accent"
                >
                  <option value="visual_style">Visual Style & Rendering</option>
                  <option value="character_identity">Character Model Sheet</option>
                  <option value="layout_composition">Webtoon Layout & Framing</option>
                  <option value="environment">Environment & Lighting</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-studio-400 mb-1">
                  Label / Description
                </label>
                <input
                  type="text"
                  value={label}
                  onChange={(e) => setLabel(e.target.value)}
                  placeholder="e.g. Manhwa Ink & Shading Reference"
                  className="w-full px-3 py-1.5 bg-studio-900 border border-studio-700 rounded-lg text-xs text-white focus:outline-none focus:border-studio-accent"
                />
              </div>

              <label className="block border-2 border-dashed border-studio-700 hover:border-studio-accent rounded-lg p-4 text-center cursor-pointer transition bg-studio-900/40">
                <ImageIcon className="w-6 h-6 text-studio-400 mx-auto mb-1" />
                <span className="text-xs font-semibold text-studio-200 block">Choose Image</span>
                <span className="text-[10px] text-studio-500">PNG, JPG, WebP</span>
                <input type="file" accept="image/*" onChange={handleUploadImage} className="hidden" />
              </label>
            </div>
          </div>

          {/* Reference Assets List */}
          <div>
            <h3 className="text-xs font-bold text-studio-400 uppercase tracking-wider mb-2">
              Uploaded References ({references.length})
            </h3>
            <div className="grid grid-cols-2 gap-2">
              {references.map((ref) => (
                <div key={ref.id} className="group relative bg-studio-900 border border-studio-800 rounded-lg overflow-hidden shadow">
                  <div className="aspect-square bg-studio-950 flex items-center justify-center overflow-hidden">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={getStorageUrl(ref.storage_key)}
                      alt={ref.label}
                      className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                    />
                  </div>
                  <div className="p-2">
                    <span className="text-[10px] font-bold text-studio-accent uppercase block truncate">
                      {ref.role.replace("_", " ")}
                    </span>
                    <span className="text-xs font-medium text-studio-200 block truncate" title={ref.label}>
                      {ref.label}
                    </span>
                    <span className="text-[10px] text-studio-500 block">
                      {ref.width}x{ref.height} • {(ref.width > 0 ? "OK" : "")}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Structured Visual Style Profile */}
        <div className="lg:col-span-2">
          {!activeVersion ? (
            <div className="border border-dashed border-studio-700 rounded-xl p-12 text-center bg-studio-850/40">
              <Palette className="w-12 h-12 text-studio-500 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-studio-200">No Visual Style Profile</h3>
              <p className="text-xs text-studio-400 max-w-sm mx-auto mt-1 mb-4">
                Upload one or more reference images on the left and click &quot;Extract Style Profile&quot; to establish your project&apos;s canonical rendering rules.
              </p>
            </div>
          ) : (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-6 shadow space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-studio-800">
                <div>
                  <h3 className="text-base font-bold text-white">
                    Visual Style Profile (Version {activeVersion.version_number})
                  </h3>
                  <span className="text-xs text-studio-400">
                    Art-directed parameters derived from {activeVersion.reference_asset_ids?.length || references.length} reference(s).
                  </span>
                </div>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                  activeVersion.is_approved ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-amber-950 text-amber-400 border border-amber-800"
                }`}>
                  {activeVersion.is_approved ? "APPROVED" : "DRAFT (AWAITING REVIEW)"}
                </span>
              </div>

              {/* Color Palette Chips */}
              <div>
                <label className="text-xs font-bold text-studio-400 uppercase tracking-wider block mb-2">
                  Harmonized Color Palette
                </label>
                <div className="flex items-center space-x-2">
                  {activeVersion.palette_and_colors?.map((hex: string, idx: number) => (
                    <div key={idx} className="flex flex-col items-center space-y-1">
                      <div
                        className="w-10 h-10 rounded-lg border border-white/20 shadow"
                        style={{ backgroundColor: hex }}
                      />
                      <span className="text-[10px] text-studio-400 font-mono">{hex}</span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-studio-400 mt-2">
                  <span className="font-semibold text-studio-300">Relationships:</span> {activeVersion.color_relationships}
                </p>
              </div>

              {/* Core Artistic Properties */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Linework & Contours</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.linework_and_contours}</p>
                </div>

                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Anatomy & Proportions</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.anatomy_and_proportions}</p>
                </div>

                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Facial Construction & Expressions</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.facial_features_and_expressions}</p>
                </div>

                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Shading & Lighting Behavior</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.shading_and_lighting}</p>
                </div>

                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Texture & Rendering</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.texture_and_rendering}</p>
                </div>

                <div className="p-3 bg-studio-900 border border-studio-800 rounded-lg">
                  <span className="font-bold text-studio-accent block mb-1">Background Treatment</span>
                  <p className="text-studio-300 leading-relaxed">{activeVersion.background_treatment}</p>
                </div>
              </div>

              {/* Reference Isolation Assurance (Requirement 2.1) */}
              <div className="p-3 bg-studio-900/80 border border-studio-cyan/40 rounded-lg text-xs">
                <span className="font-bold text-studio-cyan flex items-center space-x-1.5 mb-1">
                  <Shield className="w-3.5 h-3.5" />
                  <span>Reference Isolation Verified (Canon Protection)</span>
                </span>
                <p className="text-studio-300 leading-relaxed">{activeVersion.reference_isolation_notes}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
