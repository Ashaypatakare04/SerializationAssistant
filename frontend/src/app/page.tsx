"use client";

import React, { useState, useEffect } from "react";
import { Project, StoryBible, StyleProfile, AdaptationPlan, Episode, SourceDocument, ReferenceAsset } from "../types";
import { api } from "../lib/api";
import { Navbar } from "../components/Navbar";
import { ProjectDashboard } from "../components/ProjectDashboard";
import { SourceWorkspace } from "../components/SourceWorkspace";
import { ReferenceStyleWorkspace } from "../components/ReferenceStyleWorkspace";
import { SerializationWorkspace } from "../components/SerializationWorkspace";
import { StoryboardEditor } from "../components/StoryboardEditor";
import { IllustrationReview } from "../components/IllustrationReview";
import { WebtoonReader } from "../components/WebtoonReader";
import { QAReportModal } from "../components/QAReportModal";
import { CapabilitiesModal } from "../components/CapabilitiesModal";
import { StudioSettingsModal } from "../components/StudioSettingsModal";

export default function StudioHome() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState<string>("source");
  const [showDashboard, setShowDashboard] = useState<boolean>(false);
  const [showQAModal, setShowQAModal] = useState<boolean>(false);
  const [showCapabilitiesModal, setShowCapabilitiesModal] = useState<boolean>(false);
  const [showSettingsModal, setShowSettingsModal] = useState<boolean>(false);
  const [activeRole, setActiveRole] = useState<string>("owner");

  // Loaded project artifacts
  const [storyBible, setStoryBible] = useState<StoryBible | null>(null);
  const [styleProfile, setStyleProfile] = useState<StyleProfile | null>(null);
  const [adaptationPlans, setAdaptationPlans] = useState<AdaptationPlan[]>([]);
  const [selectedEpisode, setSelectedEpisode] = useState<Episode | null>(null);
  const [documents, setDocuments] = useState<SourceDocument[]>([]);
  const [references, setReferences] = useState<ReferenceAsset[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const loadProjects = React.useCallback(async () => {
    setGlobalError(null);
    try {
      const me = await api.getMe().catch(() => null);
      if (me?.role) setActiveRole(me.role);
      const data = await api.getProjects();
      setProjects(data);
      if (data.length > 0) {
        setCurrentProject((prev) => prev || data[0]);
      } else if (data.length === 0) {
        setShowDashboard(true);
      }
    } catch (err: any) {
      console.error("Failed to load projects", err);
      setGlobalError(err?.message || "Unable to connect to backend API. Check Studio Settings.");
      setShowDashboard(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const loadProjectDetails = React.useCallback(async (projectId: string) => {
    try {
      const [proj, docs, refs] = await Promise.all([
        api.getProject(projectId),
        api.getDocuments(projectId).catch(() => []),
        api.getReferences(projectId).catch(() => []),
      ]);
      setCurrentProject(proj);
      setDocuments(docs);
      setReferences(refs);

      // Load story bible if exists
      api.getStoryBible(projectId).then(setStoryBible).catch(() => setStoryBible(null));

      // Load style profile if exists
      api.getStyleProfile(projectId).then(setStyleProfile).catch(() => setStyleProfile(null));

      // Load adaptation plans & first episode
      api.getAdaptationPlans(projectId).then((plans) => {
        setAdaptationPlans(plans);
        if (plans.length > 0 && plans[0].episodes?.length > 0) {
          api.getEpisode(plans[0].episodes[0].id).then(setSelectedEpisode).catch(() => {});
        } else {
          setSelectedEpisode(null);
        }
      }).catch(() => setAdaptationPlans([]));

    } catch (err) {
      console.error("Failed to load project details", err);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    if (currentProject?.id) {
      loadProjectDetails(currentProject.id);
    }
  }, [currentProject?.id, loadProjectDetails]);


  const handleCreateProject = async (title: string, description: string, genre: string) => {
    const newProj = await api.createProject({
      title,
      description,
      configuration: { genre },
    });
    setProjects([newProj, ...projects]);
    setCurrentProject(newProj);
    setShowDashboard(false);
    setActiveTab("source");
  };

  const handleSeedDemoPilot = async () => {
    setIsLoading(true);
    setGlobalError(null);
    try {
      // 1. Create Demo Project
      const demoProject = await api.createProject({
        title: "Shadows in the Rain (8-Panel Pilot Demo)",
        description: "Atmospheric urban mystery webtoon pilot with Min-jun and Soo-jin.",
        configuration: { genre: "Urban Mystery / Drama" }
      });

      // 2. Upload demo manuscript
      const demoManuscript = `# Chapter 1: Shadows in the Rain

Min-jun adjusted the collar of his trench coat against the heavy rain. 
The streetlight above the alleyway flickered, illuminating the puddle at his feet.
Water dripped steadily from the rusted metal sign overhead.

Soo-jin emerged from the doorway of the vintage cafe. "You're seven minutes late," she said.
"The bridge was blocked by police checkpoints," Min-jun whispered, pulling the sealed dossier from inside his jacket.

"Did you read what's inside?" Soo-jin frowned, her knuckles tightening around her umbrella.
"I didn't need to," Min-jun murmured. "The list was never buried. And your name is on the second page."`;

      const docFormData = new FormData();
      docFormData.append("raw_text", demoManuscript);
      docFormData.append("filename", "shadows_in_the_rain_chapter1.md");
      await api.uploadDocument(demoProject.id, docFormData);

      // 3. Upload a stylized reference image
      // Create a 1x1 base64 transparent PNG for demo reference
      const dummyPngBase64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";
      const blob = await fetch(`data:image/png;base64,${dummyPngBase64}`).then(res => res.blob());
      const refFormData = new FormData();
      refFormData.append("file", blob, "demo_manhwa_style_sheet.png");
      refFormData.append("role", "visual_style");
      refFormData.append("label", "Modern Korean Manhwa - Ink & Dramatic Lighting");
      await api.uploadReference(demoProject.id, refFormData);

      // 4. Run Story Analysis & Style Analysis in parallel
      const [storyJob, styleJob] = await Promise.all([
        api.triggerStoryAnalysis(demoProject.id),
        api.triggerStyleAnalysis(demoProject.id),
      ]);
      await Promise.all([
        api.pollJob(storyJob.id),
        api.pollJob(styleJob.id),
      ]);

      // 5. Generate Adaptation Plan
      const planJob = await api.triggerAdaptationPlan(demoProject.id);
      await api.pollJob(planJob.id);

      // 6. Get episode and generate storyboard
      const plans = await api.getAdaptationPlans(demoProject.id);
      const epId = plans[0].episodes[0].id;
      const sbJob = await api.triggerStoryboard(epId);
      await api.pollJob(sbJob.id);

      // 7. Auto-approve panel 1 and draft art for demo
      const ep = await api.getEpisode(epId);
      const panels: any[] = [];
      ep.scenes.forEach((s) => s.beats.forEach((b) => panels.push(...b.panels)));
      if (panels.length > 0) {
        await api.recordApproval({
          artifact_type: "panel",
          artifact_id: panels[0].id,
          artifact_version: panels[0].version,
          approved_by: "lead_creator",
          comments: "Pilot opening approved"
        });
        const genJob = await api.triggerPanelGeneration(panels[0].id, "draft");
        await api.pollJob(genJob.id);
      }

      await loadProjects();
      setCurrentProject(demoProject);
      setShowDashboard(false);
      setActiveTab("storyboard");
    } catch (err: any) {
      console.error("Failed to seed demo pilot", err);
      setGlobalError(err?.message || "Failed to load demo pilot. Check backend connection in Settings.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    if (currentProject) {
      await loadProjectDetails(currentProject.id);
    }
  };

  return (
    <div className="min-h-screen bg-studio-900 text-studio-100 flex flex-col font-sans">
      <Navbar
        currentProject={currentProject}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenDashboard={() => setShowDashboard(true)}
        onOpenQA={() => setShowQAModal(true)}
        onOpenCapabilities={() => setShowCapabilitiesModal(true)}
        onOpenSettings={() => setShowSettingsModal(true)}
        activeRole={activeRole}
      />

      <main className="flex-1 pb-16">
        {globalError && (
          <div className="max-w-6xl mx-auto px-4 pt-4">
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-700 text-rose-200 text-xs flex items-center justify-between gap-3">
              <span>{globalError}</span>
              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => setShowSettingsModal(true)}
                  className="px-2.5 py-1 rounded bg-rose-800 hover:bg-rose-700 text-white font-semibold"
                >
                  Open Settings
                </button>
                <button
                  onClick={() => setGlobalError(null)}
                  className="px-2 py-1 rounded text-rose-300 hover:text-white"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}

        {showDashboard || !currentProject ? (
          <ProjectDashboard
            projects={projects}
            isLoadingDemo={isLoading}
            onSelectProject={(proj) => {
              setCurrentProject(proj);
              setShowDashboard(false);
            }}
            onCreateProject={handleCreateProject}
            onSeedDemoProject={handleSeedDemoPilot}
          />
        ) : (
          <>
            {activeTab === "source" && (
              <SourceWorkspace
                project={currentProject}
                storyBible={storyBible}
                documents={documents}
                onRefresh={handleRefresh}
              />
            )}

            {activeTab === "style" && (
              <ReferenceStyleWorkspace
                project={currentProject}
                references={references}
                styleProfile={styleProfile}
                onRefresh={handleRefresh}
              />
            )}

            {activeTab === "planning" && (
              <SerializationWorkspace
                project={currentProject}
                adaptationPlans={adaptationPlans}
                selectedEpisode={selectedEpisode}
                onSelectEpisode={setSelectedEpisode}
                onRefresh={handleRefresh}
                onProceedToStoryboard={() => setActiveTab("storyboard")}
              />
            )}

            {activeTab === "storyboard" && (
              <StoryboardEditor
                episode={selectedEpisode}
                onRefresh={handleRefresh}
                onProceedToReview={() => setActiveTab("illustration")}
              />
            )}

            {activeTab === "illustration" && (
              <IllustrationReview
                episode={selectedEpisode}
                onRefresh={handleRefresh}
                onProceedToReader={() => setActiveTab("reader")}
              />
            )}

            {activeTab === "reader" && (
              <WebtoonReader
                episode={selectedEpisode}
                onRefresh={handleRefresh}
              />
            )}
          </>
        )}
      </main>

      {/* QA Audit Modal */}
      {showQAModal && (
        <QAReportModal
          episodeId={selectedEpisode?.id || null}
          onClose={() => setShowQAModal(false)}
        />
      )}

      {/* AI Capabilities Modal */}
      {showCapabilitiesModal && (
        <CapabilitiesModal
          onClose={() => setShowCapabilitiesModal(false)}
        />
      )}

      {/* Studio Settings & RBAC Role Modal */}
      {showSettingsModal && (
        <StudioSettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
          currentProjectId={currentProject?.id}
          onRoleChanged={(r) => setActiveRole(r)}
        />
      )}
    </div>
  );
}
