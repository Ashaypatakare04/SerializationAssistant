"use client";

import React, { useState } from "react";
import { Project } from "../types";
import { Plus, FolderGit2, Calendar, FileText, ArrowRight, Sparkles } from "lucide-react";

interface ProjectDashboardProps {
  projects: Project[];
  onSelectProject: (project: Project) => void;
  onCreateProject: (title: string, description: string, genre: string) => Promise<void>;
  onSeedDemoProject: () => Promise<void>;
}

export const ProjectDashboard: React.FC<ProjectDashboardProps> = ({
  projects,
  onSelectProject,
  onCreateProject,
  onSeedDemoProject,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [genre, setGenre] = useState("Urban Mystery / Drama");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setIsSubmitting(true);
    try {
      await onCreateProject(title, description, genre);
      setShowModal(false);
      setTitle("");
      setDescription("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-10 px-4">
      {/* Top Hero Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-8 border-b border-studio-700/60">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            AI Novel-to-Webtoon Studio
          </h1>
          <p className="text-sm text-studio-400 mt-1 max-w-xl">
            Creator-controlled production pipeline transforming original manuscripts into reference-faithful, 
            vertically scrolling webtoons with strict identity consistency and human approval gates.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={onSeedDemoProject}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-200 transition shadow"
          >
            <Sparkles className="w-4 h-4 text-studio-accent" />
            <span>Load Demo Pilot</span>
          </button>

          <button
            onClick={() => setShowModal(true)}
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow-lg"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="mt-8">
        <h2 className="text-base font-semibold text-studio-200 mb-4 flex items-center space-x-2">
          <FolderGit2 className="w-4 h-4 text-studio-accent" />
          <span>Your Projects ({projects.length})</span>
        </h2>

        {projects.length === 0 ? (
          <div className="border border-dashed border-studio-700 rounded-xl p-12 text-center bg-studio-850/40">
            <FolderGit2 className="w-12 h-12 text-studio-500 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-studio-200">No projects yet</h3>
            <p className="text-xs text-studio-400 max-w-sm mx-auto mt-1 mb-4">
              Create a new serialization project or load the pre-configured 8-panel pilot demo to experience the end-to-end studio.
            </p>
            <button
              onClick={() => setShowModal(true)}
              className="px-4 py-2 bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white rounded-lg transition"
            >
              Create Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => onSelectProject(proj)}
                className="group cursor-pointer bg-studio-850 border border-studio-750 hover:border-studio-accent/70 rounded-xl p-5 transition flex flex-col justify-between shadow hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase rounded bg-studio-800 text-studio-cyan border border-studio-700">
                      {proj.current_stage.replace("_", " ")}
                    </span>
                    <span className="text-[11px] text-studio-500 flex items-center space-x-1">
                      <Calendar className="w-3 h-3" />
                      <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                    </span>
                  </div>

                  <h3 className="font-bold text-white text-base group-hover:text-studio-accent transition line-clamp-1">
                    {proj.title}
                  </h3>
                  <p className="text-xs text-studio-400 mt-1 line-clamp-2">
                    {proj.description || "No description provided."}
                  </p>
                </div>

                <div className="mt-5 pt-3 border-t border-studio-800 flex items-center justify-between text-xs text-studio-400">
                  <span className="flex items-center space-x-1">
                    <FileText className="w-3.5 h-3.5 text-studio-500" />
                    <span>{proj.documents?.length || 0} Documents</span>
                  </span>
                  <span className="text-studio-accent flex items-center space-x-1 font-medium group-hover:translate-x-0.5 transition">
                    <span>Open Studio</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-studio-850 border border-studio-700 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h2 className="text-lg font-bold text-white">Create New Serialization Project</h2>
            <p className="text-xs text-studio-400 mt-1 mb-4">
              Enter basic project metadata to initialize your creative workspace.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-studio-300 mb-1">
                  Project Title *
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Shadows in the Rain"
                  className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded-lg text-sm text-white focus:outline-none focus:border-studio-accent"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-studio-300 mb-1">
                  Genre
                </label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded-lg text-sm text-white focus:outline-none focus:border-studio-accent"
                >
                  <option value="Urban Mystery / Drama">Urban Mystery / Drama</option>
                  <option value="Fantasy / Action">Fantasy / Action</option>
                  <option value="Romance / Slice of Life">Romance / Slice of Life</option>
                  <option value="Sci-Fi / Cyberpunk">Sci-Fi / Cyberpunk</option>
                  <option value="Psychological Thriller">Psychological Thriller</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-studio-300 mb-1">
                  Description / Synopsis
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief synopsis or adaptation goals..."
                  className="w-full px-3 py-2 bg-studio-900 border border-studio-700 rounded-lg text-sm text-white focus:outline-none focus:border-studio-accent"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-studio-750 text-xs font-semibold text-studio-300 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition disabled:opacity-50"
                >
                  {isSubmitting ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
