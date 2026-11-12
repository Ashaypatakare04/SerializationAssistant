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

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const override = localStorage.getItem("studio_api_url");
    if (override) return override;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
}

export function setApiBaseUrl(url: string): void {
  if (typeof window !== "undefined") {
    if (!url) {
      localStorage.removeItem("studio_api_url");
    } else {
      localStorage.setItem("studio_api_url", url.trim().replace(/\/+$/, ""));
    }
  }
}

export function getStorageUrl(storageKey: string): string {
  if (!storageKey) return "";
  if (storageKey.startsWith("http")) return storageKey;
  return `${getApiBaseUrl()}/storage/${storageKey}`;
}

export function getAuthToken(): string {
  if (typeof window !== "undefined") {
    const stored = localStorage.getItem("studio_auth_token");
    if (stored) return stored;
  }
  return "creator_default_user";
}

export function setAuthToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("studio_auth_token", token);
  }
}

export function getStoredUserId(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("studio_user_id") || "studio_creator";
  }
  return "studio_creator";
}

export function setStoredIdentity(userId: string, role: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("studio_user_id", userId);
    localStorage.setItem("studio_user_role", role);
  }
}

function isSignedToken(token: string | null): boolean {
  if (!token) return false;
  const parts = token.split(".");
  return parts.length === 2 && parts[0].length > 0 && parts[1].length > 0;
}

let pendingTokenPromise: Promise<string> | null = null;

export async function ensureAuthToken(forceRefresh = false): Promise<string> {
  if (typeof window === "undefined") {
    return getAuthToken();
  }

  const stored = localStorage.getItem("studio_auth_token");
  if (!forceRefresh && isSignedToken(stored)) {
    return stored as string;
  }

  if (pendingTokenPromise) {
    return pendingTokenPromise;
  }

  const userId = localStorage.getItem("studio_user_id") || "studio_creator";
  const role = localStorage.getItem("studio_user_role") || "owner";

  pendingTokenPromise = (async () => {
    const response = await fetch(`${getApiBaseUrl()}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, role }),
    });
    if (!response.ok) {
      throw new Error(`Authentication failed (${response.status} ${response.statusText})`);
    }
    const data = await response.json();
    setAuthToken(data.access_token);
    setStoredIdentity(data.user_id, data.role);
    return data.access_token as string;
  })();

  try {
    return await pendingTokenPromise;
  } finally {
    pendingTokenPromise = null;
  }
}

async function fetchWithAuth(url: string, options: RequestInit = {}, skipAuthBootstrap = false): Promise<Response> {
  const token = skipAuthBootstrap ? getAuthToken() : await ensureAuthToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> | undefined),
    "X-Studio-Auth": token,
    "Authorization": `Bearer ${token}`,
  };

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 && !skipAuthBootstrap) {
    const refreshedToken = await ensureAuthToken(true);
    response = await fetch(url, {
      ...options,
      headers: {
        ...headers,
        "X-Studio-Auth": refreshedToken,
        "Authorization": `Bearer ${refreshedToken}`,
      },
    });
  }

  return response;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${getApiBaseUrl()}${endpoint}`;
  const isTokenEndpoint = endpoint === "/auth/token";
  const response = await fetchWithAuth(url, options, isTokenEndpoint);

  if (!response.ok) {
    let errorDetail = response.statusText || `HTTP ${response.status}`;
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
  triggerAssetEdit: (assetId: string, data: { instruction: string; target_region?: string; mask_base64?: string }) =>
    request<Job>(`/assets/${assetId}/edit-jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),
  triggerPanelInpaint: (panelId: string, data: { instruction: string; target_region?: string; mask_base64?: string }) =>
    request<Job>(`/panels/${panelId}/inpaint`, {
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
      const response = await fetchWithAuth(`${getApiBaseUrl()}/jobs/${jobId}/stream`, {
        headers: {
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
  triggerExport: (episodeId: string, requireApproved = true, includeSpeechBubbles = true) =>
    request<Job>(`/episodes/${episodeId}/export-jobs?require_all_approved=${requireApproved}&include_speech_bubbles=${includeSpeechBubbles}`, {
      method: "POST",
    }),
  getExport: (exportId: string) =>
    request<any>(`/exports/${exportId}`),
  downloadExportZip: async (exportId: string): Promise<void> => {
    const response = await fetchWithAuth(`${getApiBaseUrl()}/exports/${exportId}/download`);
    if (!response.ok) {
      let detail = response.statusText || "Export download failed.";
      try {
        const err = await response.json();
        detail = err.detail || detail;
      } catch {
        // ignore parse failure
      }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = `webtoon_export_${exportId.slice(0, 8)}.zip`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  },

  fetchStorageBlob: async (storageKey: string): Promise<Blob> => {
    const url = getStorageUrl(storageKey);
    const response = await fetchWithAuth(url);
    if (!response.ok) {
      throw new Error(`Failed to load asset (${response.status})`);
    }
    return response.blob();
  },

  // Capabilities
  getCapabilities: () =>
    request<any>("/system/capabilities"),

  // Auth, Roles & Diagnostics
  issueToken: (data: { user_id: string; role: string; expires_in?: number }) =>
    request<{ access_token: string; token_type: string; user_id: string; role: string }>("/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }),

  getMe: () =>
    request<{ user_id: string; role: string }>("/auth/me"),

  getQuota: (projectId: string) =>
    request<{
      project_id: string;
      daily_used_generations: number;
      daily_quota_limit: number;
      remaining_generations: number;
    }>(`/auth/quota/${projectId}`),

  checkHealth: async (): Promise<boolean> => {
    try {
      const apiBase = getApiBaseUrl();
      const healthUrl = apiBase.replace(/\/api\/v1\/?$/, "/health");
      const res = await fetch(healthUrl, { method: "GET" });
      return res.ok;
    } catch {
      return false;
    }
  },
};
