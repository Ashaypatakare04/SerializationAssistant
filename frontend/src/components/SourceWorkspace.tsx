"use client";

import React, { useState } from "react";
import { Project, StoryBible, SourceDocument } from "../types";
import { api } from "../lib/api";
import {
  UploadCloud,
  FileText,
  Sparkles,
  Users,
  CheckCircle,
  AlertTriangle,
  Clock,
  BookOpen,
  Edit2,
  Save,
  Check
} from "lucide-react";

interface SourceWorkspaceProps {
  project: Project;
  storyBible: StoryBible | null;
  documents: SourceDocument[];
  onRefresh: () => Promise<void>;
}

export const SourceWorkspace: React.FC<SourceWorkspaceProps> = ({
  project,
  storyBible,
  documents,
  onRefresh,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"documents" | "bible" | "characters" | "continuity">("documents");
  const [rawText, setRawText] = useState("");
  const [filename, setFilename] = useState("manuscript_chapter1.md");
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Edit Mode state for Story Bible
  const [isEditingBible, setIsEditingBible] = useState(false);
  const [editedPremise, setEditedPremise] = useState(storyBible?.premise || "");
  const [editedTone, setEditedTone] = useState(storyBible?.narrative_tone || "");

  const handleUploadText = async () => {
    if (!rawText.trim()) return;
    setIsUploading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("raw_text", rawText);
      formData.append("filename", filename);
      await api.uploadDocument(project.id, formData);
      setRawText("");
      setMessage({ type: "success", text: "Manuscript text ingested and partitioned into sections successfully." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to upload document." });
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await api.uploadDocument(project.id, formData);
      setMessage({ type: "success", text: `File '${file.name}' ingested successfully.` });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Upload failed." });
    } finally {
      setIsUploading(false);
    }
  };

  const handleRunStoryAnalysis = async () => {
    setIsAnalyzing(true);
    setMessage(null);
    try {
      const job = await api.triggerStoryAnalysis(project.id);
      await api.pollJob(job.id);
      setMessage({ type: "success", text: "Story Analysis completed! Story Bible & Character records generated." });
      await onRefresh();
      setActiveSubTab("bible");
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Story analysis failed." });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleApproveBible = async () => {
    if (!storyBible) return;
    setIsApproving(true);
    try {
      await api.recordApproval({
        artifact_type: "story_bible",
        artifact_id: storyBible.id,
        artifact_version: storyBible.version,
        approved_by: "creator",
        comments: "Story understanding, character identities, and continuity rules approved."
      });
      setMessage({ type: "success", text: "Story Bible approved! You can now proceed to Serialization Planning." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Approval failed." });
    } finally {
      setIsApproving(false);
    }
  };

  const handleSaveBibleEdits = async () => {
    if (!storyBible) return;
    try {
      await api.updateStoryBible(storyBible.id, {
        premise: editedPremise,
        narrative_tone: editedTone
      });
      setIsEditingBible(false);
      setMessage({ type: "success", text: "Story Bible modifications saved." });
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to update story bible." });
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <BookOpen className="w-5 h-5 text-studio-accent" />
            <span>Source Ingestion & Story Bible</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Ingest original manuscript, extract characters and plot continuity facts, and approve canon before adaptation.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {documents.length > 0 && (
            <button
              onClick={handleRunStoryAnalysis}
              disabled={isAnalyzing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-200 transition disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4 text-studio-cyan" />
              <span>{isAnalyzing ? "Analyzing..." : "Run Story Analysis"}</span>
            </button>
          )}

          {storyBible && (
            <button
              onClick={handleApproveBible}
              disabled={isApproving || storyBible.status === "approved"}
              className={`flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold transition ${
                storyBible.status === "approved"
                  ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800 cursor-default"
                  : "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg"
              }`}
            >
              <CheckCircle className="w-4 h-4" />
              <span>{storyBible.status === "approved" ? "Bible Approved (Gate Passed)" : "Approve Story Bible"}</span>
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

      {/* Sub Tabs */}
      <div className="flex space-x-2 border-b border-studio-800 mb-6">
        <button
          onClick={() => setActiveSubTab("documents")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
            activeSubTab === "documents"
              ? "border-studio-accent text-white"
              : "border-transparent text-studio-400 hover:text-studio-200"
          }`}
        >
          Manuscript Ingestion ({documents.length})
        </button>
        <button
          onClick={() => setActiveSubTab("bible")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
            activeSubTab === "bible"
              ? "border-studio-accent text-white"
              : "border-transparent text-studio-400 hover:text-studio-200"
          }`}
        >
          Story Bible {storyBible ? `(v${storyBible.version})` : ""}
        </button>
        <button
          onClick={() => setActiveSubTab("characters")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
            activeSubTab === "characters"
              ? "border-studio-accent text-white"
              : "border-transparent text-studio-400 hover:text-studio-200"
          }`}
        >
          Canonical Characters ({storyBible?.characters?.length || 0})
        </button>
        <button
          onClick={() => setActiveSubTab("continuity")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition ${
            activeSubTab === "continuity"
              ? "border-studio-accent text-white"
              : "border-transparent text-studio-400 hover:text-studio-200"
          }`}
        >
          Continuity & Events ({storyBible?.events?.length || 0})
        </button>
      </div>

      {/* Tab 1: Documents & Ingestion */}
      {activeSubTab === "documents" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
            <h3 className="text-sm font-bold text-white mb-2 flex items-center space-x-2">
              <UploadCloud className="w-4 h-4 text-studio-accent" />
              <span>Add Manuscript</span>
            </h3>
            <p className="text-xs text-studio-400 mb-4">
              Upload a .txt or .md file, or paste your novel text directly.
            </p>

            <div className="space-y-4">
              <label className="block border-2 border-dashed border-studio-700 hover:border-studio-accent rounded-lg p-4 text-center cursor-pointer transition bg-studio-900/40">
                <FileText className="w-6 h-6 text-studio-400 mx-auto mb-1" />
                <span className="text-xs font-semibold text-studio-200 block">Upload Manuscript File</span>
                <span className="text-[10px] text-studio-500">.txt, .md, .json (max 10MB)</span>
                <input type="file" accept=".txt,.md,.markdown" onChange={handleFileUpload} className="hidden" />
              </label>

              <div className="text-center text-[11px] text-studio-500 font-medium">OR DIRECT TEXT ENTRY</div>

              <div>
                <input
                  type="text"
                  value={filename}
                  onChange={(e) => setFilename(e.target.value)}
                  placeholder="Filename (e.g. chapter1.md)"
                  className="w-full px-3 py-1.5 bg-studio-900 border border-studio-700 rounded-lg text-xs text-white mb-2 focus:outline-none focus:border-studio-accent"
                />
                <textarea
                  rows={6}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Paste novel chapter or scene text here..."
                  className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded-lg text-xs text-white focus:outline-none focus:border-studio-accent"
                />
                <button
                  onClick={handleUploadText}
                  disabled={isUploading || !rawText.trim()}
                  className="w-full mt-2 py-2 bg-studio-750 hover:bg-studio-700 text-xs font-semibold text-white rounded-lg transition disabled:opacity-50"
                >
                  {isUploading ? "Ingesting..." : "Ingest Text"}
                </button>
              </div>
            </div>
          </div>

          <div className="lg:col-span-2 space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center justify-between">
              <span>Ingested Documents & Partitioned Sections</span>
              <span className="text-xs text-studio-400 font-normal">{documents.length} File(s)</span>
            </h3>

            {documents.length === 0 ? (
              <div className="border border-studio-800 rounded-xl p-8 text-center bg-studio-850/40 text-xs text-studio-400">
                No documents uploaded yet. Add your manuscript on the left to begin story analysis.
              </div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="bg-studio-850 border border-studio-750 rounded-xl p-4 shadow">
                  <div className="flex items-center justify-between mb-3 pb-2 border-b border-studio-800">
                    <div className="flex items-center space-x-2">
                      <FileText className="w-4 h-4 text-studio-accent" />
                      <span className="font-bold text-sm text-white">{doc.filename}</span>
                    </div>
                    <div className="flex items-center space-x-3 text-xs text-studio-400">
                      <span>{doc.word_count.toLocaleString()} Words</span>
                      <span>{doc.char_count.toLocaleString()} Chars</span>
                      <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-950 border border-emerald-800 text-emerald-400">
                        {doc.extraction_status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="text-[11px] font-semibold text-studio-400 uppercase tracking-wider">
                      Extracted Chapters & Sections ({doc.sections?.length || 0}):
                    </div>
                    <div className="max-h-56 overflow-y-auto space-y-2 pr-1">
                      {doc.sections?.map((sec) => (
                        <div key={sec.id} className="p-2.5 rounded bg-studio-900 border border-studio-800 text-xs">
                          <div className="font-semibold text-studio-cyan mb-1 flex items-center justify-between">
                            <span>Section {sec.section_index}: {sec.title}</span>
                            <span className="text-[10px] text-studio-500">[{sec.start_char} - {sec.end_char}]</span>
                          </div>
                          <p className="text-studio-300 line-clamp-3 leading-relaxed">{sec.content}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Story Bible */}
      {activeSubTab === "bible" && (
        <div className="space-y-6">
          {!storyBible ? (
            <div className="border border-dashed border-studio-700 rounded-xl p-10 text-center bg-studio-850/40">
              <BookOpen className="w-10 h-10 text-studio-500 mx-auto mb-2" />
              <p className="text-xs text-studio-400">
                Story Bible has not been generated yet. Please upload a manuscript and click &quot;Run Story Analysis&quot;.
              </p>
            </div>
          ) : (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-6 shadow">
              <div className="flex items-center justify-between pb-4 border-b border-studio-800 mb-5">
                <div>
                  <h3 className="text-base font-bold text-white">Canonical Story Bible (Version {storyBible.version})</h3>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded mt-1 inline-block ${
                    storyBible.status === "approved" ? "bg-emerald-950 text-emerald-400 border border-emerald-800" : "bg-amber-950 text-amber-400 border border-amber-800"
                  }`}>
                    STATUS: {storyBible.status.toUpperCase()}
                  </span>
                </div>

                {!isEditingBible ? (
                  <button
                    onClick={() => {
                      setEditedPremise(storyBible.premise);
                      setEditedTone(storyBible.narrative_tone);
                      setIsEditingBible(true);
                    }}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-750 hover:bg-studio-700 text-xs font-semibold text-studio-200"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                    <span>Edit Facts</span>
                  </button>
                ) : (
                  <button
                    onClick={handleSaveBibleEdits}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>Save Changes</span>
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="text-xs font-bold text-studio-400 uppercase tracking-wider block mb-1">
                    Premise & Core Conflict
                  </label>
                  {isEditingBible ? (
                    <textarea
                      rows={3}
                      value={editedPremise}
                      onChange={(e) => setEditedPremise(e.target.value)}
                      className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded text-xs text-white"
                    />
                  ) : (
                    <p className="text-xs text-studio-200 leading-relaxed bg-studio-900/50 p-3 rounded-lg border border-studio-800">
                      {storyBible.premise}
                    </p>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-studio-400 uppercase tracking-wider block mb-1">
                    Narrative Tone & Visual Atmosphere
                  </label>
                  {isEditingBible ? (
                    <input
                      type="text"
                      value={editedTone}
                      onChange={(e) => setEditedTone(e.target.value)}
                      className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded text-xs text-white"
                    />
                  ) : (
                    <p className="text-xs text-studio-200 leading-relaxed bg-studio-900/50 p-3 rounded-lg border border-studio-800">
                      {storyBible.narrative_tone}
                    </p>
                  )}
                </div>

                <div>
                  <label className="text-xs font-bold text-studio-400 uppercase tracking-wider block mb-1">
                    Established World Rules ({storyBible.world_rules?.length || 0})
                  </label>
                  <div className="space-y-1.5">
                    {storyBible.world_rules?.map((rule: any, idx: number) => (
                      <div key={idx} className="p-2 bg-studio-900 border border-studio-800 rounded text-xs text-studio-300">
                        • {typeof rule === "string" ? rule : rule.rule || JSON.stringify(rule)}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-xs font-bold text-studio-400 uppercase tracking-wider block mb-1">
                    Core Themes
                  </label>
                  <div className="flex flex-wrap gap-1.5">
                    {storyBible.themes?.map((th: any, idx: number) => (
                      <span key={idx} className="px-2.5 py-1 rounded bg-studio-800 border border-studio-700 text-xs text-studio-300 font-medium">
                        {typeof th === "string" ? th : th.theme || JSON.stringify(th)}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Characters Bible */}
      {activeSubTab === "characters" && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white flex items-center space-x-2">
            <Users className="w-4 h-4 text-studio-accent" />
            <span>Canonical Characters ({storyBible?.characters?.length || 0})</span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {storyBible?.characters?.map((char) => {
              const activeVer = char.versions?.[0];
              return (
                <div key={char.id} className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
                  <div className="flex items-center justify-between pb-2 border-b border-studio-800 mb-3">
                    <div>
                      <h4 className="font-bold text-white text-base">{char.canonical_name}</h4>
                      <span className="text-[11px] text-studio-400 capitalize">{char.role}</span>
                    </div>
                    {char.aliases?.length > 0 && (
                      <span className="text-[10px] text-studio-500">Aliases: {char.aliases.join(", ")}</span>
                    )}
                  </div>

                  <div className="space-y-2.5 text-xs">
                    <div>
                      <span className="text-studio-500 font-semibold block">Personality & Voice:</span>
                      <p className="text-studio-300 mt-0.5">{char.personality_summary}</p>
                    </div>

                    {activeVer && (
                      <div className="bg-studio-900/60 p-3 rounded-lg border border-studio-800 space-y-1.5">
                        <div className="text-[10px] font-bold text-studio-accent uppercase tracking-wider">
                          Canonical Appearance Profile
                        </div>
                        <div>
                          <span className="text-studio-400 font-medium">Hair:</span>{" "}
                          <span className="text-studio-200">{activeVer.hair_style_and_color}</span>
                        </div>
                        <div>
                          <span className="text-studio-400 font-medium">Clothing:</span>{" "}
                          <span className="text-studio-200">{activeVer.clothing_and_accessories}</span>
                        </div>
                        <div>
                          <span className="text-studio-400 font-medium">Distinctive Features:</span>{" "}
                          <span className="text-studio-200">{activeVer.distinctive_features}</span>
                        </div>
                        <div>
                          <span className="text-studio-400 font-medium">Proportions:</span>{" "}
                          <span className="text-studio-200">{activeVer.body_proportions}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 4: Continuity & Events */}
      {activeSubTab === "continuity" && (
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-bold text-white mb-3">Chronological Plot Events & Source Traceability</h3>
            <div className="space-y-2">
              {storyBible?.events?.map((ev) => (
                <div key={ev.id} className="p-3 bg-studio-850 border border-studio-750 rounded-xl flex items-start justify-between text-xs">
                  <div>
                    <span className="font-bold text-studio-accent block">
                      Beat {ev.chronological_order}: {ev.title}
                    </span>
                    <p className="text-studio-300 mt-1">{ev.summary}</p>
                  </div>
                  <span className="px-2 py-0.5 rounded bg-studio-800 border border-studio-700 text-[10px] text-studio-cyan shrink-0 ml-4">
                    Source: {ev.source_locator || "Section"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-bold text-white mb-3">Continuity Rules & Constraints</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {storyBible?.continuity_facts?.map((fact) => (
                <div key={fact.id} className="p-3 bg-studio-850 border border-studio-750 rounded-xl text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-studio-cyan uppercase text-[10px] tracking-wider">
                      [{fact.category}]
                    </span>
                    <span className="text-[10px] text-studio-500">{fact.source_locator}</span>
                  </div>
                  <p className="text-studio-300">{fact.statement}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
