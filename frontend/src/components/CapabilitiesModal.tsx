"use client";

import React, { useState, useEffect } from "react";
import { api } from "../lib/api";
import { Info, X, Cpu, DollarSign, CheckCircle2, AlertCircle } from "lucide-react";

interface CapabilitiesModalProps {
  onClose: () => void;
}

export const CapabilitiesModal: React.FC<CapabilitiesModalProps> = ({ onClose }) => {
  const [capabilities, setCapabilities] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCapabilities()
      .then((data) => setCapabilities(data))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4">
      <div className="bg-studio-850 border border-studio-700 rounded-2xl max-w-lg w-full shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-studio-750">
          <div className="flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-studio-cyan" />
            <h3 className="font-bold text-white text-base">AI Engine & Capability Inspection</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 text-studio-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5 text-xs">
          {loading ? (
            <div className="text-center py-6 text-studio-400">Inspecting system capabilities...</div>
          ) : capabilities ? (
            <>
              {/* Active Provider Tag */}
              <div className="p-3.5 bg-studio-900 border border-studio-800 rounded-xl space-y-2">
                <span className="font-bold text-studio-accent uppercase text-[10px] tracking-wider block">
                  Active Generation Runtime
                </span>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">
                    LLM: {capabilities.active_llm_provider?.toUpperCase()} • Image: {capabilities.active_image_provider?.toUpperCase()}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-studio-accent/20 text-studio-accent border border-studio-accent/30">
                    Active
                  </span>
                </div>
              </div>

              {/* Provider Capabilities Breakdown */}
              <div className="space-y-3">
                <h4 className="text-[11px] font-bold text-studio-300 uppercase tracking-wider">
                  Supported Model Providers:
                </h4>

                {Object.entries(capabilities.providers || {}).map(([key, prov]: [string, any]) => (
                  <div key={key} className="p-3 bg-studio-900/60 border border-studio-800 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-xs">{prov.provider_name}</span>
                      {prov.is_real_ai ? (
                        prov.is_configured ? (
                          <span className="flex items-center space-x-1 text-emerald-400 text-[10px] font-semibold">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Configured</span>
                          </span>
                        ) : (
                          <span className="flex items-center space-x-1 text-amber-400 text-[10px] font-semibold">
                            <AlertCircle className="w-3 h-3" />
                            <span>Key Missing</span>
                          </span>
                        )
                      ) : (
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-studio-800 text-studio-cyan border border-studio-700 uppercase">
                          Offline Mock Mode
                        </span>
                      )}
                    </div>

                    <div className="text-[11px] text-studio-400 space-y-0.5">
                      {prov.supported_aspect_ratios && (
                        <div>
                          <span className="text-studio-500 font-medium">Aspect Ratios:</span>{" "}
                          <span>{prov.supported_aspect_ratios.join(", ")}</span>
                        </div>
                      )}
                      <div>
                        <span className="text-studio-500 font-medium">Inpainting:</span>{" "}
                        <span className="text-studio-300">{prov.supports_inpainting ? "Supported" : "N/A"}</span>
                      </div>
                      <div>
                        <span className="text-studio-500 font-medium">Cost / Final Panel:</span>{" "}
                        <span className="text-emerald-400 font-mono">${(prov.cost_per_final_usd || 0).toFixed(3)}</span>
                      </div>
                      {prov.status_message && (
                        <div className="text-[10px] text-studio-500 italic mt-1">
                          Status: {prov.status_message}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-studio-400">Unable to retrieve system capabilities.</div>
          )}
        </div>
      </div>
    </div>
  );
};
