"use client";

import React, { useState, useEffect } from "react";
import { FullQAReport, QAFinding } from "../types";
import { api } from "../lib/api";
import { ShieldCheck, X, AlertTriangle, CheckCircle, Info, RefreshCw } from "lucide-react";

interface QAReportModalProps {
  episodeId: string | null;
  onClose: () => void;
}

export const QAReportModal: React.FC<QAReportModalProps> = ({ episodeId, onClose }) => {
  const [report, setReport] = useState<FullQAReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadReport = () => {
    if (!episodeId) return;
    setIsLoading(true);
    api.getQAReport(episodeId)
      .then((rep) => setReport(rep))
      .catch((err) => console.error(err))
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadReport();
  }, [episodeId]);

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
      <div className="bg-studio-850 border border-studio-700 rounded-2xl max-w-2xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-studio-750">
          <div className="flex items-center space-x-2.5">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h3 className="font-bold text-white text-base">Quality Assurance & Audit Gate</h3>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={loadReport}
              disabled={isLoading}
              className="p-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 text-studio-400 hover:text-white"
              title="Re-run QA Checks"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 text-studio-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          {!report ? (
            <div className="text-center py-8 text-studio-400 text-xs">
              {isLoading ? "Running automated narrative, visual, and sequence QA checks..." : "No QA report available."}
            </div>
          ) : (
            <>
              {/* Overall Status Banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${
                  report.overall_status === "passed"
                    ? "bg-emerald-950/50 border-emerald-800 text-emerald-300"
                    : "bg-amber-950/50 border-amber-800 text-amber-300"
                }`}
              >
                <div>
                  <span className="font-bold text-sm block">
                    {report.overall_status === "passed" ? "All QA Checks Cleared" : "Review Recommended"}
                  </span>
                  <span className="text-xs text-studio-400 mt-0.5 block">
                    {report.overall_status === "passed"
                      ? "Zero blocking continuity, narrative, or aspect ratio errors detected."
                      : "Non-blocking warnings flagged below for creator review."}
                  </span>
                </div>
                <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-studio-900 border border-current">
                  {report.overall_status}
                </span>
              </div>

              {/* Three Diagnostic Pillars */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* 1. Narrative QA */}
                <div className="p-3 bg-studio-900 border border-studio-800 rounded-xl text-xs space-y-1">
                  <span className="text-studio-500 font-bold uppercase text-[10px] block">Narrative Fidelity</span>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-white">{report.narrative.score.toFixed(0)}%</span>
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <span className="text-[10px] text-studio-400">Events & Continuity linked</span>
                </div>

                {/* 2. Visual QA */}
                <div className="p-3 bg-studio-900 border border-studio-800 rounded-xl text-xs space-y-1">
                  <span className="text-studio-500 font-bold uppercase text-[10px] block">Visual Consistency</span>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-white">{report.visual.score.toFixed(0)}%</span>
                    <CheckCircle className="w-4 h-4 text-studio-cyan" />
                  </div>
                  <span className="text-[10px] text-studio-400">Style & character references</span>
                </div>

                {/* 3. Sequence QA */}
                <div className="p-3 bg-studio-900 border border-studio-800 rounded-xl text-xs space-y-1">
                  <span className="text-studio-500 font-bold uppercase text-[10px] block">Sequence & Flow</span>
                  <div className="flex items-center justify-between">
                    <span className="text-lg font-bold text-white">{report.sequence.score.toFixed(0)}%</span>
                    <CheckCircle className="w-4 h-4 text-studio-accent" />
                  </div>
                  <span className="text-[10px] text-studio-400">Framing diversity & reading order</span>
                </div>
              </div>

              {/* Findings List */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-studio-300 uppercase tracking-wider">
                  Audit Findings & Recommendations:
                </h4>

                {[...report.narrative.findings, ...report.visual.findings, ...report.sequence.findings].length === 0 ? (
                  <div className="p-4 rounded-xl bg-studio-900/60 border border-studio-800 text-center text-xs text-studio-400">
                    No anomalies or warnings detected across narrative, visual, and sequential checks.
                  </div>
                ) : (
                  [...report.narrative.findings, ...report.visual.findings, ...report.sequence.findings].map((f, i) => (
                    <div
                      key={i}
                      className="p-3 bg-studio-900 border border-studio-800 rounded-xl text-xs flex items-start space-x-3"
                    >
                      {f.severity === "error" ? (
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      ) : (
                        <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      )}
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-white">{f.title}</span>
                          <span className="px-1.5 py-0.2 rounded text-[9px] uppercase font-semibold bg-studio-800 text-studio-400">
                            {f.category}
                          </span>
                        </div>
                        <p className="text-studio-300 mt-0.5 leading-relaxed">{f.description}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
