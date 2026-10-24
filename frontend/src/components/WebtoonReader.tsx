"use client";

import React, { useState, useEffect } from "react";
import { Episode, Panel, Asset } from "../types";
import { api, getStorageUrl } from "../lib/api";
import {
  Download,
  Smartphone,
  Maximize2,
  CheckCircle,
  AlertTriangle,
  Layers,
  MessageSquare,
  Sparkles,
  FileArchive
} from "lucide-react";

interface WebtoonReaderProps {
  episode: Episode | null;
  onRefresh: () => Promise<void>;
}

export const WebtoonReader: React.FC<WebtoonReaderProps> = ({
  episode,
  onRefresh,
}) => {
  const [isMobileFrame, setIsMobileFrame] = useState(true);
  const [showOverlayText, setShowOverlayText] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [exportDownloadUrl, setExportDownloadUrl] = useState<string | null>(null);
  const [panelAssetMap, setPanelAssetMap] = useState<Record<string, string>>({});
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const allPanels = React.useMemo(() => {
    const panels: Panel[] = [];
    episode?.scenes?.forEach((s) => {
      s.beats?.forEach((b) => {
        panels.push(...b.panels);
      });
    });
    panels.sort((a, b) => a.panel_number - b.panel_number);
    return panels;
  }, [episode]);

  useEffect(() => {
    if (allPanels.length > 0) {
      // Fetch latest assets for all panels
      Promise.all(
        allPanels.map(async (p) => {
          try {
            const assets = await api.getPanelAssets(p.id);
            const active = assets[0]?.versions?.[assets[0].versions.length - 1];
            return { panelId: p.id, url: active?.storage_key ? getStorageUrl(active.storage_key) : "" };
          } catch {
            return { panelId: p.id, url: "" };
          }
        })
      ).then((results) => {
        const map: Record<string, string> = {};
        results.forEach((r) => {
          if (r.url) map[r.panelId] = r.url;
        });
        setPanelAssetMap(map);
      });
    }
  }, [allPanels]);


  if (!episode || allPanels.length === 0) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-4 text-center">
        <Smartphone className="w-12 h-12 text-studio-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-studio-200">No Panels to Preview</h3>
        <p className="text-xs text-studio-400 mt-1">
          Generate panels in Storyboard to preview the vertical webtoon reader.
        </p>
      </div>
    );
  }

  const handleExportEpisode = async () => {
    setIsExporting(true);
    setMessage(null);
    setExportDownloadUrl(null);
    try {
      const job = await api.triggerExport(episode.id, true);
      const finishedJob = await api.pollJob(job.id);
      if (finishedJob.status === "failed") {
        throw new Error(finishedJob.error_message || "Export failed: All panels must be approved before publishing.");
      }
      const exportId = finishedJob.result_data?.export_id;
      if (exportId) {
        const downloadUrl = `http://127.0.0.1:8000/api/v1/exports/${exportId}/download`;
        setExportDownloadUrl(downloadUrl);
        setMessage({
          type: "success",
          text: `Episode compiled into mobile slices and packaged with manifest.json!`
        });
      }
      await onRefresh();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Export failed: All panels must be approved before publishing." });
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Top Controls Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Smartphone className="w-5 h-5 text-studio-accent" />
            <span>Vertical Webtoon Reader: {episode.title}</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Continuous vertical scrolling view with mobile readability simulation, speech bubbles layer, and export compiler.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* Frame Toggle */}
          <button
            onClick={() => setIsMobileFrame(!isMobileFrame)}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-800 hover:bg-studio-700 border border-studio-700 text-xs font-semibold text-studio-300"
          >
            {isMobileFrame ? <Maximize2 className="w-3.5 h-3.5" /> : <Smartphone className="w-3.5 h-3.5" />}
            <span>{isMobileFrame ? "Full Width" : "Mobile View (420px)"}</span>
          </button>

          {/* Dialogue Overlay Toggle */}
          <button
            onClick={() => setShowOverlayText(!showOverlayText)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition ${
              showOverlayText
                ? "bg-studio-800 border-studio-accent text-studio-accent"
                : "bg-studio-850 border-studio-700 text-studio-400"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Lettering Layer</span>
          </button>

          {/* Export Action */}
          <button
            onClick={handleExportEpisode}
            disabled={isExporting}
            className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{isExporting ? "Compiling Webtoon..." : "Export Episode"}</span>
          </button>

          {exportDownloadUrl && (
            <a
              href={exportDownloadUrl}
              download
              className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition shadow"
            >
              <FileArchive className="w-4 h-4" />
              <span>Download ZIP</span>
            </a>
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

      {/* Reader Container */}
      <div className="flex justify-center">
        <div
          className={`transition-all duration-300 ${
            isMobileFrame
              ? "w-[430px] border-4 border-studio-700 rounded-3xl bg-black p-2.5 shadow-2xl"
              : "w-full max-w-2xl bg-black p-4 rounded-xl border border-studio-800"
          }`}
        >
          {isMobileFrame && (
            <div className="w-32 h-4 bg-studio-800 rounded-full mx-auto mb-3 flex items-center justify-center">
              <div className="w-2.5 h-2.5 rounded-full bg-studio-900" />
            </div>
          )}

          {/* Vertical Scrolling Panels Canvas */}
          <div className="space-y-4 max-h-[800px] overflow-y-auto pr-1">
            {allPanels.map((panel) => {
              const imgUrl = panelAssetMap[panel.id];
              return (
                <div key={panel.id} className="relative group">
                  {/* Panel Artwork */}
                  <div className="relative aspect-[4/5] bg-studio-950 rounded-lg overflow-hidden border border-studio-800 flex items-center justify-center">
                    {imgUrl ? (
                      /* eslint-disable-next-line @next/next/no-img-element */
                      <img
                        src={imgUrl}
                        alt={`Panel ${panel.panel_number}`}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="p-6 text-center text-studio-600">
                        <Sparkles className="w-8 h-8 mx-auto mb-1 opacity-30" />
                        <span className="text-xs">Panel #{panel.panel_number}</span>
                      </div>
                    )}

                    {/* Speech Bubbles and Lettering Layer */}
                    {showOverlayText && panel.dialogues?.map((d) => (
                      <div
                        key={d.id}
                        className={`absolute z-10 max-w-[85%] ${
                          d.segment_type === "caption"
                            ? "top-3 left-3 bg-black/85 text-white border border-studio-700 px-3 py-1.5 rounded text-[11px] font-serif shadow-lg"
                            : d.segment_type === "sound_effect"
                            ? "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-studio-accent font-extrabold text-lg tracking-widest uppercase drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]"
                            : "bottom-4 right-4 bg-white text-gray-900 px-3.5 py-2 rounded-2xl text-[11px] font-sans font-medium shadow-xl border border-gray-400"
                        }`}
                      >
                        {d.speaker_name && d.segment_type === "speech_bubble" && (
                          <span className="text-[9px] font-bold text-studio-accent block uppercase">
                            {d.speaker_name}
                          </span>
                        )}
                        <span>{d.text_content}</span>
                      </div>
                    ))}
                  </div>

                  {/* Vertical breathing room spacer */}
                  <div style={{ height: `${Math.min(panel.vertical_spacing_after_px, 100)}px` }} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
