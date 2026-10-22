"use client";

import React from "react";
import { Project } from "../types";
import { Layers, ShieldCheck, Sparkles, BookOpen, Palette, Film, Eye, Download, Info } from "lucide-react";

interface NavbarProps {
  currentProject: Project | null;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onOpenDashboard: () => void;
  onOpenQA: () => void;
  onOpenCapabilities: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentProject,
  activeTab,
  setActiveTab,
  onOpenDashboard,
  onOpenQA,
  onOpenCapabilities,
}) => {
  const tabs = [
    { id: "source", label: "1. Story Bible", icon: BookOpen },
    { id: "style", label: "2. Style & Refs", icon: Palette },
    { id: "planning", label: "3. Serialization", icon: Film },
    { id: "storyboard", label: "4. Storyboard", icon: Layers },
    { id: "illustration", label: "5. Illustrations", icon: Sparkles },
    { id: "reader", label: "6. Webtoon Preview", icon: Eye },
  ];

  return (
    <header className="border-b border-studio-700 bg-studio-900/90 backdrop-blur sticky top-0 z-40 px-4 py-2.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand & Project Selector */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onOpenDashboard}
            className="flex items-center space-x-2 text-left hover:opacity-80 transition"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-studio-accent to-studio-rose flex items-center justify-center font-bold text-white shadow-md">
              WS
            </div>
            <div>
              <span className="font-bold text-sm tracking-wide text-white block">
                Novel-to-Webtoon Studio
              </span>
              <span className="text-xs text-studio-400">
                {currentProject ? currentProject.title : "No Project Selected"}
              </span>
            </div>
          </button>

          {currentProject && (
            <span className="px-2.5 py-0.5 text-xs font-medium rounded-full bg-studio-800 text-studio-300 border border-studio-700">
              Stage: {currentProject.current_stage.replace("_", " ").toUpperCase()}
            </span>
          )}
        </div>

        {/* Workflow Stages Navigation */}
        {currentProject && (
          <nav className="hidden md:flex items-center space-x-1">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    isActive
                      ? "bg-studio-accent text-white shadow-sm"
                      : "text-studio-300 hover:bg-studio-800 hover:text-white"
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        )}

        {/* Right Tools (QA, Capabilities, Project Switcher) */}
        <div className="flex items-center space-x-2">
          {currentProject && (
            <button
              onClick={onOpenQA}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-studio-200 text-xs font-medium transition"
              title="Inspect Quality Assurance Report"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="hidden sm:inline">QA Gate</span>
            </button>
          )}

          <button
            onClick={onOpenCapabilities}
            className="flex items-center space-x-1 px-2.5 py-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-studio-200 text-xs font-medium transition"
            title="Inspect AI Engine & Hardware Capabilities"
          >
            <Info className="w-3.5 h-3.5 text-studio-cyan" />
            <span className="hidden sm:inline">AI Engine</span>
          </button>

          <button
            onClick={onOpenDashboard}
            className="px-3 py-1.5 rounded-lg bg-studio-750 hover:bg-studio-700 text-xs font-medium text-white transition"
          >
            Projects
          </button>
        </div>
      </div>
    </header>
  );
};
