import {
  Project,
  SourceDocument,
  StoryBible,
  StyleProfile,
  AdaptationPlan,
  Episode,
  Panel,
  Asset,
  Job,
  FullQAReport,
  ReferenceAsset
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";

export function getStorageUrl(storageKey: string): string {
  if (!storageKey) return "";
  if (storageKey.startsWith("http")) return storageKey;
  return `${API_BASE}/storage/${storageKey}`;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "X-Studio-Auth": "creator_default_user",
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>("/projects"),
  createProject: (data: { title: string; description?: string; configuration?: any }) =>
    request<Project>("/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getProject: (id: string) => request<Project>(`/projects/${id}`),

  // Documents
  uploadDocument: (projectId: string, formData: FormData) =>
    request<SourceDocument>(`/projects/${projectId}/documents`, {
      method: "POST",
      body: formData,
    }),
  getDocuments: (projectId: string) =>
    request<SourceDocument[]>(`/projects/${projectId}/documents`),

  // References
  uploadReference: (projectId: string, formData: FormData) =>
    request<ReferenceAsset>(`/projects/${projectId}/references`, {
      method: "POST",
      body: formData,
    }),
  getReferences: (projectId: string, role?: string) =>
    request<ReferenceAsset[]>(`/projects/${projectId}/references${role ? `?role=${role}` : ""}`),

  // Story Analysis
  triggerStoryAnalysis: (projectId: string) =>
    request<Job>(`/projects/${projectId}/analysis-jobs`, { method: "POST" }),
  getStoryBible: (projectId: string) =>
    request<StoryBible>(`/projects/${projectId}/story-bible`),
  updateStoryBible: (bibleId: string, data: Partial<StoryBible>) =>
    request<StoryBible>(`/story-bibles/${bibleId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Style Analysis
  triggerStyleAnalysis: (projectId: string) =>
    request<Job>(`/projects/${projectId}/style-analysis-jobs`, { method: "POST" }),
  getStyleProfile: (projectId: string) =>
    request<StyleProfile>(`/projects/${projectId}/style-profile`),
  updateStyleProfileVersion: (profileId: string, versionNumber: number, data: any) =>
    request<any>(`/style-profiles/${profileId}/versions/${versionNumber}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Adaptation Planning
  triggerAdaptationPlan: (projectId: string) =>
    request<Job>(`/projects/${projectId}/adaptation-plans`, { method: "POST" }),
  getAdaptationPlans: (projectId: string) =>
    request<AdaptationPlan[]>(`/projects/${projectId}/adaptation-plans`),
  getEpisode: (episodeId: string) =>
    request<Episode>(`/episodes/${episodeId}`),

  // Storyboard
  triggerStoryboard: (episodeId: string) =>
    request<Job>(`/episodes/${episodeId}/storyboard-jobs`, { method: "POST" }),
  updatePanel: (panelId: string, data: Partial<Panel>) =>
    request<Panel>(`/panels/${panelId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Generation
  triggerPanelGeneration: (panelId: string, stage: "draft" | "final") =>
    request<Job>(`/panels/${panelId}/generation-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ stage }),
    }),
  triggerAssetEdit: (assetId: string, data: { instruction: string; target_region?: string }) =>
    request<Job>(`/assets/${assetId}/edit-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  getPanelAssets: (panelId: string) =>
    request<Asset[]>(`/panels/${panelId}/assets`),

  // Approvals
  recordApproval: (data: { artifact_type: string; artifact_id: string; artifact_version: number; approved_by: string; comments?: string }) =>
    request<any>(`/artifacts/${data.artifact_id}/approvals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  // Jobs & SSE Streaming
  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),
  cancelJob: (jobId: string) => request<Job>(`/jobs/${jobId}/cancel`, { method: "POST" }),
  
  streamJob: async (jobId: string, onProgress?: (job: Job) => void): Promise<Job> => {
    try {
      const response = await fetch(`${API_BASE}/jobs/${jobId}/stream`, {
        headers: {
          "X-Studio-Auth": "creator_default_user",
          "Accept": "text/event-stream",
        },
      });

      if (!response.ok || !response.body) {
        return await api._fallbackPollJob(jobId, onProgress);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
          if (dataLine) {
            const rawJson = dataLine.replace(/^data:\s*/, "");
            const job: Job = JSON.parse(rawJson);
            if (onProgress) onProgress(job);

            if (job.status === "completed") {
              reader.cancel();
              return job;
            }
            if (job.status === "failed") {
              reader.cancel();
              throw new Error(job.error_message || `Background job ${jobId} failed.`);
            }
            if (job.status === "cancelled") {
              reader.cancel();
              throw new Error(`Background job ${jobId} was cancelled.`);
            }
          }
        }
      }

      return await api.getJob(jobId);
    } catch (err: any) {
      if (err.message && (err.message.includes("failed") || err.message.includes("cancelled"))) {
        throw err;
      }
      return await api._fallbackPollJob(jobId, onProgress);
    }
  },

  _fallbackPollJob: async (jobId: string, onProgress?: (job: Job) => void, intervalMs = 800): Promise<Job> => {
    while (true) {
      const job = await request<Job>(`/jobs/${jobId}`);
      if (onProgress) onProgress(job);
      if (job.status === "completed") return job;
      if (job.status === "failed") throw new Error(job.error_message || `Background job ${jobId} failed.`);
      if (job.status === "cancelled") throw new Error(`Background job ${jobId} was cancelled.`);
      await new Promise((r) => setTimeout(r, intervalMs));
    }
  },

  pollJob: async (jobId: string, onProgress?: (job: Job) => void): Promise<Job> => {
    return api.streamJob(jobId, onProgress);
  },

  // QA
  getQAReport: (episodeId: string) =>
    request<FullQAReport>(`/episodes/${episodeId}/qa-report`),

  // Export
  triggerExport: (episodeId: string, requireApproved = true) =>
    request<Job>(`/episodes/${episodeId}/export-jobs?require_all_approved=${requireApproved}`, {
      method: "POST",
    }),
  getExport: (exportId: string) =>
    request<any>(`/exports/${exportId}`),

  // Capabilities
  getCapabilities: () =>
    request<any>("/system/capabilities"),
};
