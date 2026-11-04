"use client";

import React, { useState, useEffect, useRef } from "react";
import { Episode, Panel, Asset, AssetVersion } from "../types";
import { api, getStorageUrl } from "../lib/api";
import {
  Sparkles,
  CheckCircle,
  RefreshCw,
  Wand2,
  AlertCircle,
  Sliders,
  DollarSign,
  Clock,
  Layers,
  ArrowRight,
  ShieldAlert,
  Paintbrush,
  Eraser,
  RotateCcw,
  Eye,
  Brush
} from "lucide-react";

interface IllustrationReviewProps {
  episode: Episode | null;
  onRefresh: () => Promise<void>;
  onProceedToReader: () => void;
}

export const IllustrationReview: React.FC<IllustrationReviewProps> = ({
  episode,
  onRefresh,
  onProceedToReader,
}) => {
  const [selectedPanel, setSelectedPanel] = useState<Panel | null>(null);
  const [panelAssets, setPanelAssets] = useState<Asset[]>([]);
  const [editInstruction, setEditInstruction] = useState("");
  const [targetRegion, setTargetRegion] = useState("face");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>("");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Inpainting Canvas Brush State
  const [isBrushMode, setIsBrushMode] = useState(false);
  const [brushSize, setBrushSize] = useState(30);
  const [isEraser, setIsEraser] = useState(false);
  const [hasMaskDrawn, setHasMaskDrawn] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const isDrawingRef = useRef(false);

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
    if (allPanels.length > 0 && !selectedPanel) {
      setSelectedPanel(allPanels[0]);
    }
  }, [allPanels, selectedPanel]);

  useEffect(() => {
    if (selectedPanel) {
      api.getPanelAssets(selectedPanel.id).then((assets) => {
        setPanelAssets(assets);
      }).catch(() => {
        setPanelAssets([]);
      });
      // Reset mask when switching panel
      clearCanvas();
      setIsBrushMode(false);
    }
  }, [selectedPanel]);

  // Adjust canvas size when image loads or window resizes
  const syncCanvasDimensions = () => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (canvas && img) {
      canvas.width = img.clientWidth || 800;
      canvas.height = img.clientHeight || 1000;
    }
  };

  useEffect(() => {
    if (isBrushMode) {
      syncCanvasDimensions();
    }
  }, [isBrushMode]);

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    setHasMaskDrawn(false);
  };

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    isDrawingRef.current = true;
    const rect = canvas.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    const x = clientX - rect.left;
    const y = clientY - rect.top;

    ctx.beginPath();
    ctx.moveTo(x, y);
    drawStroke(x, y);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement> | React.TouchEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clientX = "touches" in e ? e.touches[0].clientX : e.clientX;
    const clientY = "touches" in e ? e.touches[0].clientY : e.clientY;
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    drawStroke(x, y);
  };

  const stopDrawing = () => {
    isDrawingRef.current = false;
    const canvas = canvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx?.closePath();
    }
  };

  const drawStroke = (x: number, y: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.lineWidth = brushSize;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (isEraser) {
      ctx.globalCompositeOperation = "destination-out";
    } else {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = "rgba(236, 72, 153, 0.65)";
      ctx.fillStyle = "rgba(236, 72, 153, 0.65)";
    }

    ctx.lineTo(x, y);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(x, y, brushSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x, y);

    setHasMaskDrawn(true);
  };

  const exportBinaryMask = (): string | null => {
    const canvas = canvasRef.current;
    if (!canvas || !hasMaskDrawn) return null;

    // Create offscreen mask canvas of same size
    const offscreen = document.createElement("canvas");
    offscreen.width = canvas.width;
    offscreen.height = canvas.height;
    const offCtx = offscreen.getContext("2d");
    if (!offCtx) return null;

    // 1. Fill entire canvas with black (unmasked)
    offCtx.fillStyle = "#000000";
    offCtx.fillRect(0, 0, offscreen.width, offscreen.height);

    // 2. Read drawn canvas pixels; convert painted regions to white
    const srcCtx = canvas.getContext("2d");
    if (!srcCtx) return null;
    const imgData = srcCtx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imgData.data;

    const maskImgData = offCtx.getImageData(0, 0, offscreen.width, offscreen.height);
    const maskData = maskImgData.data;

    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3];
      if (alpha > 20) {
        // Masked area -> pure white
        maskData[i] = 255;
        maskData[i + 1] = 255;
        maskData[i + 2] = 255;
        maskData[i + 3] = 255;
      } else {
        // Unmasked area -> pure black
        maskData[i] = 0;
        maskData[i + 1] = 0;
        maskData[i + 2] = 0;
        maskData[i + 3] = 255;
      }
    }

    offCtx.putImageData(maskImgData, 0, 0);
    return offscreen.toDataURL("image/png");
  };

  if (!episode || allPanels.length === 0) {
    return (
      <div className="max-w-6xl mx-auto py-12 px-4 text-center">
        <Sparkles className="w-12 h-12 text-studio-500 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-studio-200">No Storyboard Panels Found</h3>
        <p className="text-xs text-studio-400 mt-1">
          Please create and approve storyboard panels before reviewing illustrations.
        </p>
      </div>
    );
  }

  const activeAsset = panelAssets[0];
  const activeVersion = activeAsset?.versions?.[activeAsset.versions.length - 1];

  const handleGenerateFinal = async () => {
    if (!selectedPanel) return;
    if (!selectedPanel.is_approved) {
      setMessage({
        type: "error",
        text: "Approval Gate Warning: Panel must be approved in Storyboard before generating final illustration."
      });
      return;
    }

    setIsProcessing(true);
    setProcessingStatus("Initiating high-resolution generation...");
    setMessage(null);
    try {
      const job = await api.triggerPanelGeneration(selectedPanel.id, "final");
      await api.streamJob(job.id, (j) => {
        setProcessingStatus(`${j.stage_description} (${j.progress_percentage}%)`);
      });
      setMessage({ type: "success", text: `Final artwork generated for Panel ${selectedPanel.panel_number}!` });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Final generation failed." });
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  const handleApplyEditOrInpaint = async () => {
    if (!activeAsset || !editInstruction.trim() || !selectedPanel) return;
    setIsProcessing(true);
    setMessage(null);
    setProcessingStatus("Preparing targeted inpaint request...");

    try {
      let maskDataUrl: string | undefined = undefined;
      if (isBrushMode && hasMaskDrawn) {
        const mask = exportBinaryMask();
        if (mask) maskDataUrl = mask;
      }

      const job = await api.triggerPanelInpaint(selectedPanel.id, {
        instruction: editInstruction,
        target_region: targetRegion,
        mask_base64: maskDataUrl
      });

      await api.streamJob(job.id, (j) => {
        setProcessingStatus(`${j.stage_description} (${j.progress_percentage}%)`);
      });

      setEditInstruction("");
      clearCanvas();
      setIsBrushMode(false);
      setMessage({
        type: "success",
        text: maskDataUrl
          ? `Localized inpaint applied using custom painted brush mask!`
          : `Targeted correction applied to [${targetRegion}]!`
      });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Edit / inpaint failed." });
    } finally {
      setIsProcessing(false);
      setProcessingStatus("");
    }
  };

  const handleApproveAssetVersion = async () => {
    if (!activeVersion) return;
    setIsProcessing(true);
    try {
      await api.recordApproval({
        artifact_type: "asset_version",
        artifact_id: activeVersion.id,
        artifact_version: activeVersion.version_number,
        approved_by: "creator",
        comments: "Illustration accepted for final episode webtoon publication."
      });
      setMessage({ type: "success", text: `Illustration version ${activeVersion.version_number} approved!` });
      await onRefresh();
      const assets = await api.getPanelAssets(selectedPanel!.id);
      setPanelAssets(assets);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Approval failed." });
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-6 px-4">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-studio-700/60 mb-6">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Sparkles className="w-5 h-5 text-studio-accent" />
            <span>Illustration Review & Correction Studio</span>
          </h2>
          <p className="text-xs text-studio-400 mt-0.5">
            Inspect illustrations against canonical references, paint localized inpainting masks, and approve finished webtoon panels.
          </p>
        </div>

        <button
          onClick={onProceedToReader}
          className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition shadow"
        >
          <span>Preview Webtoon Strip</span>
          <ArrowRight className="w-4 h-4" />
        </button>
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

      {/* Main Review Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Panel Selector Strip */}
        <div className="lg:col-span-1 space-y-2">
          <h3 className="text-xs font-bold text-studio-400 uppercase tracking-wider mb-2">
            Episode Panels ({allPanels.length})
          </h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {allPanels.map((p) => {
              const isSelected = selectedPanel?.id === p.id;
              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPanel(p)}
                  className={`p-3 rounded-xl cursor-pointer border transition text-xs flex items-center justify-between ${
                    isSelected
                      ? "bg-studio-800 border-studio-accent shadow-md"
                      : "bg-studio-850 border-studio-750 hover:border-studio-600"
                  }`}
                >
                  <div className="flex items-center space-x-2">
                    <span className="w-6 h-6 rounded bg-studio-900 text-studio-accent font-mono font-bold flex items-center justify-center text-[11px]">
                      #{p.panel_number}
                    </span>
                    <div>
                      <span className="font-semibold text-white block capitalize">
                        {p.shot_type.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-studio-400 truncate max-w-[120px] block">
                        {p.local_emotion}
                      </span>
                    </div>
                  </div>

                  {p.is_approved ? (
                    <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <span className="text-[10px] text-amber-400 font-semibold uppercase">Pending</span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Center: Selected Panel High-Res Artwork Viewer with Interactive Mask Canvas */}
        <div className="lg:col-span-2 space-y-4">
          {selectedPanel && (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-5 shadow">
              <div className="flex items-center justify-between pb-3 border-b border-studio-800 mb-4">
                <div>
                  <h3 className="font-bold text-white text-base">
                    Panel #{selectedPanel.panel_number}: {selectedPanel.shot_type.replace("_", " ").toUpperCase()}
                  </h3>
                  <span className="text-xs text-studio-400">
                    Emotion: <span className="text-studio-accent font-medium">{selectedPanel.local_emotion}</span>
                  </span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleGenerateFinal}
                    disabled={isProcessing}
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-studio-accent hover:bg-studio-accentHover text-xs font-semibold text-white transition disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{isProcessing ? processingStatus || "Rendering..." : "Generate Final Art"}</span>
                  </button>

                  {activeVersion && (
                    <button
                      onClick={handleApproveAssetVersion}
                      disabled={isProcessing || activeVersion.is_approved}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                        activeVersion.is_approved
                          ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                          : "bg-emerald-600 hover:bg-emerald-500 text-white"
                      }`}
                    >
                      <CheckCircle className="w-3.5 h-3.5" />
                      <span>{activeVersion.is_approved ? "Art Approved" : "Approve Art"}</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Inpaint Mask Toolbar */}
              {activeVersion && (
                <div className="flex items-center justify-between bg-studio-900 border border-studio-800 rounded-lg p-2.5 mb-3 text-xs">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setIsBrushMode(!isBrushMode)}
                      className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold transition ${
                        isBrushMode
                          ? "bg-pink-600 text-white"
                          : "bg-studio-800 hover:bg-studio-750 text-studio-300"
                      }`}
                    >
                      <Brush className="w-3.5 h-3.5" />
                      <span>{isBrushMode ? "Active Mask Brush" : "Paint Inpaint Mask"}</span>
                    </button>

                    {isBrushMode && (
                      <>
                        <button
                          onClick={() => setIsEraser(false)}
                          className={`p-1.5 rounded transition ${
                            !isEraser ? "bg-pink-600/40 text-pink-300 border border-pink-500" : "text-studio-400 hover:text-white"
                          }`}
                          title="Brush Mode"
                        >
                          <Paintbrush className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => setIsEraser(true)}
                          className={`p-1.5 rounded transition ${
                            isEraser ? "bg-pink-600/40 text-pink-300 border border-pink-500" : "text-studio-400 hover:text-white"
                          }`}
                          title="Eraser Mode"
                        >
                          <Eraser className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={clearCanvas}
                          className="flex items-center space-x-1 px-2 py-1 bg-studio-800 hover:bg-studio-750 text-studio-400 hover:text-white rounded"
                          title="Clear Mask"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span className="text-[11px]">Clear</span>
                        </button>
                      </>
                    )}
                  </div>

                  {isBrushMode && (
                    <div className="flex items-center space-x-2">
                      <span className="text-[11px] text-studio-400">Size:</span>
                      <input
                        type="range"
                        min="8"
                        max="80"
                        value={brushSize}
                        onChange={(e) => setBrushSize(Number(e.target.value))}
                        className="w-20 accent-pink-500"
                      />
                      <span className="text-[10px] font-mono text-studio-300">{brushSize}px</span>
                    </div>
                  )}
                </div>
              )}

              {/* Artwork Viewport with Interactive Canvas */}
              <div className="relative aspect-[4/5] bg-studio-950 rounded-xl overflow-hidden border border-studio-800 flex items-center justify-center">
                {activeVersion ? (
                  <>
                    {/* Base Panel Artwork */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      ref={imgRef}
                      src={getStorageUrl(activeVersion.storage_key)}
                      alt={`Panel ${selectedPanel.panel_number}`}
                      onLoad={syncCanvasDimensions}
                      className="w-full h-full object-contain pointer-events-none select-none"
                    />

                    {/* Interactive Mask Brush Overlay Canvas */}
                    <canvas
                      ref={canvasRef}
                      onMouseDown={startDrawing}
                      onMouseMove={draw}
                      onMouseUp={stopDrawing}
                      onMouseLeave={stopDrawing}
                      onTouchStart={startDrawing}
                      onTouchMove={draw}
                      onTouchEnd={stopDrawing}
                      className={`absolute inset-0 w-full h-full ${
                        isBrushMode ? "cursor-crosshair z-10 pointer-events-auto" : "pointer-events-none hidden"
                      }`}
                    />
                  </>
                ) : (
                  <div className="text-center p-6 text-studio-500">
                    <Sparkles className="w-10 h-10 mx-auto mb-2 opacity-40" />
                    <p className="text-xs">No artwork generated yet for this panel.</p>
                    <p className="text-[11px] text-studio-600 mt-1">
                      Click &quot;Generate Final Art&quot; or draft in Storyboard.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Targeted Editing & Provenance Metadata */}
        <div className="lg:col-span-1 space-y-4">
          {/* Targeted Inpainting / Correction */}
          <div className="bg-studio-850 border border-studio-750 rounded-xl p-4 shadow space-y-3">
            <h4 className="text-xs font-bold text-white flex items-center space-x-1.5">
              <Wand2 className="w-3.5 h-3.5 text-studio-accent" />
              <span>Targeted Correction</span>
            </h4>
            <p className="text-[11px] text-studio-400">
              {isBrushMode && hasMaskDrawn
                ? "Custom painted mask detected! Inpainting will execute strictly inside your drawn brush area."
                : "Apply localized corrections with prompt instructions or paint an inpainting mask."}
            </p>

            {!isBrushMode && (
              <div>
                <label className="block text-[10px] font-semibold text-studio-400 mb-1">Target Region</label>
                <select
                  value={targetRegion}
                  onChange={(e) => setTargetRegion(e.target.value)}
                  className="w-full px-2 py-1.5 bg-studio-900 border border-studio-700 rounded text-xs text-white"
                >
                  <option value="face">Facial Expression & Eyes</option>
                  <option value="hair">Hair Rendering</option>
                  <option value="clothing">Clothing & Folds</option>
                  <option value="lighting">Rim Lighting / Shadows</option>
                  <option value="background">Background Perspective</option>
                </select>
              </div>
            )}

            <div>
              <label className="block text-[10px] font-semibold text-studio-400 mb-1">
                {isBrushMode ? "Inpaint Instruction" : "Correction Prompt"}
              </label>
              <textarea
                rows={3}
                value={editInstruction}
                onChange={(e) => setEditInstruction(e.target.value)}
                placeholder={
                  isBrushMode
                    ? "e.g. Draw a gentle smile, refine the hand fingers..."
                    : "e.g. Sharpen eye highlights and deepen shadow..."
                }
                className="w-full px-2 py-1.5 bg-studio-900 border border-studio-700 rounded text-xs text-white"
              />
            </div>

            <button
              onClick={handleApplyEditOrInpaint}
              disabled={isProcessing || !activeAsset || !editInstruction.trim()}
              className={`w-full py-2 text-xs font-semibold rounded transition disabled:opacity-50 flex items-center justify-center space-x-1.5 ${
                isBrushMode && hasMaskDrawn
                  ? "bg-pink-600 hover:bg-pink-500 text-white shadow-md shadow-pink-950"
                  : "bg-studio-750 hover:bg-studio-700 text-white"
              }`}
            >
              <Wand2 className="w-3.5 h-3.5" />
              <span>
                {isProcessing
                  ? processingStatus || "Inpainting..."
                  : isBrushMode && hasMaskDrawn
                  ? "Execute Masked Inpaint"
                  : "Apply Targeted Edit"}
              </span>
            </button>
          </div>

          {/* Provenance & Cost Metadata */}
          {activeVersion && (
            <div className="bg-studio-850 border border-studio-750 rounded-xl p-4 shadow text-xs space-y-2">
              <h4 className="text-[11px] font-bold text-studio-300 uppercase tracking-wider">
                Provenance & Audit
              </h4>
              <div className="space-y-1 text-studio-400">
                <div>
                  <span className="font-semibold text-studio-500">Stage:</span>{" "}
                  <span className="text-white uppercase font-bold text-[10px]">{activeVersion.stage}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Provider:</span>{" "}
                  <span className="text-studio-200">{activeVersion.provider}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Duration:</span>{" "}
                  <span className="text-studio-200">{activeVersion.duration_seconds}s</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Est. Cost:</span>{" "}
                  <span className="text-studio-emerald font-mono">${activeVersion.estimated_cost_usd.toFixed(3)}</span>
                </div>
                <div>
                  <span className="font-semibold text-studio-500">Version:</span>{" "}
                  <span className="text-studio-cyan font-mono">v{activeVersion.version_number}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
