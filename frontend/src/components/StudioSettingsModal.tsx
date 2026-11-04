"use client";

import React, { useState, useEffect } from "react";
import { X, Server, Shield, CheckCircle2, AlertCircle, RefreshCw, Zap, Key } from "lucide-react";
import { api, getApiBaseUrl, setApiBaseUrl, getAuthToken, setAuthToken } from "../lib/api";

interface StudioSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentProjectId?: string;
  onRoleChanged?: (role: string) => void;
}

export const StudioSettingsModal: React.FC<StudioSettingsModalProps> = ({
  isOpen,
  onClose,
  currentProjectId,
  onRoleChanged
}) => {
  const [apiUrl, setApiUrl] = useState<string>("");
  const [isHealthChecking, setIsHealthChecking] = useState<boolean>(false);
  const [isOnline, setIsOnline] = useState<boolean | null>(null);
  const [currentRole, setCurrentRole] = useState<string>("owner");
  const [currentUserId, setCurrentUserId] = useState<string>("studio_owner");
  const [quotaInfo, setQuotaInfo] = useState<{ used: number; limit: number } | null>(null);
  const [isUpdatingRole, setIsUpdatingRole] = useState<boolean>(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      setApiUrl(getApiBaseUrl());
      checkConnection();
      fetchMe();
      if (currentProjectId) {
        fetchQuota(currentProjectId);
      }
    }
  }, [isOpen, currentProjectId]);

  const checkConnection = async () => {
    setIsHealthChecking(true);
    try {
      const ok = await api.checkHealth();
      setIsOnline(ok);
    } catch {
      setIsOnline(false);
    } finally {
      setIsHealthChecking(false);
    }
  };

  const fetchMe = async () => {
    try {
      const me = await api.getMe();
      setCurrentRole(me.role);
      setCurrentUserId(me.user_id);
    } catch {
      // fallback
      setCurrentRole("owner");
      setCurrentUserId("creator_default_user");
    }
  };

  const fetchQuota = async (projId: string) => {
    try {
      const q = await api.getQuota(projId);
      setQuotaInfo({
        used: q.daily_used_generations,
        limit: q.daily_quota_limit
      });
    } catch {
      setQuotaInfo(null);
    }
  };

  const handleSaveApiUrl = async () => {
    setApiBaseUrl(apiUrl);
    setSaveMessage("API URL updated!");
    setTimeout(() => setSaveMessage(null), 2500);
    await checkConnection();
  };

  const handleSwitchRole = async (role: string) => {
    setIsUpdatingRole(true);
    try {
      const userId = `${role}_lead`;
      const res = await api.issueToken({ user_id: userId, role });
      setAuthToken(res.access_token);
      setCurrentRole(res.role);
      setCurrentUserId(res.user_id);
      if (onRoleChanged) {
        onRoleChanged(res.role);
      }
      setSaveMessage(`Switched role to: ${role.replace("_", " ").toUpperCase()}`);
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (err: any) {
      alert(`Failed to switch role: ${err.message}`);
    } finally {
      setIsUpdatingRole(false);
    }
  };

  if (!isOpen) return null;

  const roles = [
    { id: "owner", title: "Studio Owner", badge: "Full Access", desc: "Can manage team, edit projects, approve assets, and run generation." },
    { id: "art_director", title: "Art Director", badge: "Approval Gatekeeper", desc: "Can approve creative assets, sign off panels, and run revisions." },
    { id: "writer", title: "Script Writer", badge: "Scripting Only", desc: "Can edit dialogue and scene beats. Approval gates are restricted (HTTP 403)." },
    { id: "storyboarder", title: "Storyboarder", badge: "Layout & Framing", desc: "Can sequence panels and compose shots. Approvals restricted." },
    { id: "editor", title: "Editor", badge: "Reviewer", desc: "Proofreading and dialogue reviews. No approval authority." }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-studio-900 border border-studio-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-studio-800 flex items-center justify-between bg-studio-950/40">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-studio-800 border border-studio-700 flex items-center justify-center text-studio-accent shadow-sm">
              <Server className="w-5 h-5 text-studio-accent" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Studio Environment & Role Settings</h2>
              <p className="text-xs text-studio-400">Configure backend endpoint, test connectivity, and switch studio roles</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-studio-400 hover:text-white hover:bg-studio-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {saveMessage && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-medium flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>{saveMessage}</span>
            </div>
          )}

          {/* Section 1: Backend Connection */}
          <div className="bg-studio-800/40 border border-studio-700/60 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-studio-200 flex items-center space-x-2">
                <Zap className="w-4 h-4 text-amber-400" />
                <span>Backend API Endpoint</span>
              </span>
              <div className="flex items-center space-x-2">
                {isOnline === true ? (
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-semibold flex items-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>ONLINE</span>
                  </span>
                ) : isOnline === false ? (
                  <span className="px-2 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-[10px] font-semibold flex items-center space-x-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
                    <span>OFFLINE</span>
                  </span>
                ) : null}
                <button
                  onClick={checkConnection}
                  disabled={isHealthChecking}
                  className="p-1 text-studio-400 hover:text-white transition"
                  title="Test Connection"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${isHealthChecking ? "animate-spin text-studio-accent" : ""}`} />
                </button>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="http://127.0.0.1:8000/api/v1"
                className="flex-1 bg-studio-900 border border-studio-700 rounded-lg px-3 py-2 text-xs text-white placeholder-studio-500 focus:outline-none focus:border-studio-accent font-mono"
              />
              <button
                onClick={handleSaveApiUrl}
                className="px-3 py-2 rounded-lg bg-studio-accent hover:bg-studio-accent-hover text-white text-xs font-medium transition shadow-sm"
              >
                Save
              </button>
            </div>
            <p className="text-[11px] text-studio-400 leading-relaxed">
              When accessing from Vercel, enter your public backend URL or tunnel endpoint (e.g., <code className="text-studio-300">https://api.yourstudio.com/api/v1</code>).
            </p>
          </div>

          {/* Section 2: Studio Role & Access Control (RBAC) */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Shield className="w-4 h-4 text-studio-purple" />
                <span className="text-xs font-bold text-studio-200">Studio Role & Identity</span>
              </div>
              <span className="text-xs text-studio-400">
                Active User: <strong className="text-white">{currentUserId}</strong>
              </span>
            </div>

            <div className="grid grid-cols-1 gap-2.5">
              {roles.map((r) => {
                const isActive = currentRole === r.id;
                return (
                  <div
                    key={r.id}
                    onClick={() => handleSwitchRole(r.id)}
                    className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between ${
                      isActive
                        ? "bg-studio-accent/10 border-studio-accent shadow-sm"
                        : "bg-studio-800/30 border-studio-800 hover:border-studio-700 hover:bg-studio-800/60"
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-white">{r.title}</span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-studio-800 text-studio-300 border border-studio-700">
                          {r.badge}
                        </span>
                        {isActive && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-studio-accent text-white">
                            Active Role
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-studio-400">{r.desc}</p>
                    </div>

                    <button
                      disabled={isActive || isUpdatingRole}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                        isActive
                          ? "bg-studio-accent text-white"
                          : "bg-studio-700 hover:bg-studio-600 text-studio-200"
                      }`}
                    >
                      {isActive ? "Selected" : "Switch"}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 3: Quota Information */}
          {quotaInfo && (
            <div className="bg-studio-800/20 border border-studio-800 rounded-xl p-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-studio-300 block">24-Hour Project Generation Quota</span>
                <span className="text-[11px] text-studio-400">Protects AI cloud providers against runaway batch costs</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-bold text-white font-mono">
                  {quotaInfo.used} / {quotaInfo.limit}
                </span>
                <span className="text-[10px] text-studio-400 block">jobs in last 24h</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-studio-800 bg-studio-950/40 flex items-center justify-between">
          <span className="text-[11px] text-studio-500 font-mono flex items-center space-x-1">
            <Key className="w-3 h-3" />
            <span>JWT Zero-Trust Architecture</span>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 text-xs font-medium text-white transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
