import React, { useState, useEffect } from 'react';
import { Camera, MapPin, Type, Compass, Eye, ShieldAlert } from 'lucide-react';

export default function LandmarkTimeline({ analysis, backendUrl }) {
  const [selectedFrame, setSelectedFrame] = useState(null);
  
  const l12 = analysis?.landmark_intelligence;
  if (!l12) return null;

  const landmarks = l12.landmarks_detected || [];
  const ocrSignals = l12.ocr_signals || [];
  const sessionId = analysis.id;

  // Extract all unique frames mentioned in landmarks or OCR
  const frameIds = Array.from(new Set([
    ...landmarks.map(l => l.frame_id),
    ...ocrSignals.map(o => o.frame_id)
  ])).sort((a, b) => {
    const numA = parseInt(a.replace(/^\D+/g, ''), 10) || 0;
    const numB = parseInt(b.replace(/^\D+/g, ''), 10) || 0;
    return numA - numB;
  });

  // Select first frame by default
  useEffect(() => {
    if (frameIds.length > 0 && !selectedFrame) {
      setSelectedFrame(frameIds[0]);
    }
  }, [frameIds, selectedFrame]);

  if (frameIds.length === 0) {
    return (
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 text-center font-mono text-xs text-zinc-500">
        NO KEYFRAMES FOUND WITH VISUAL INTELLIGENCE SIGNALS
      </div>
    );
  }

  // Get data for selected frame
  const selectedNum = parseInt(selectedFrame?.replace(/^\D+/g, ''), 10) || 0;
  const frameLandmarks = landmarks.filter(l => l.frame_id === selectedFrame);
  const frameOcr = ocrSignals.filter(o => o.frame_id === selectedFrame);
  const frameCandidates = (l12.candidate_locations || []).filter(c => c.frame_id === selectedFrame);

  // Estimate a mock timestamp (e.g. Frame 15 at 30 fps = 0.5s)
  const fps = analysis.video_analysis?.fps || 30;
  const timestampSec = (selectedNum / fps).toFixed(2);

  // Determine highest tier resolved on this frame
  const getFrameMaxTier = (fId) => {
    const fL = landmarks.filter(l => l.frame_id === fId);
    if (fL.some(l => l.source === 'serpapi_knowledge_graph' || l.source === 'serpapi_visual_match')) return 'Tier 2 (Lens)';
    if (fL.some(l => l.source === 'vision_api')) return 'Tier 1 (Vision)';
    return 'Tier 0 (Moondream)';
  };

  return (
    <div className="space-y-6">
      {/* Horizontal Scroll Timeline */}
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
        <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2 font-mono">
          <Camera className="w-4 h-4 text-blue-400" /> Forensic Frame Timeline
        </h3>

        <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar snap-x">
          {frameIds.map((fId) => {
            const frameNum = parseInt(fId.replace(/^\D+/g, ''), 10) || 0;
            const isSelected = selectedFrame === fId;
            const tierStr = getFrameMaxTier(fId);
            const lCount = landmarks.filter(l => l.frame_id === fId).length;
            const oCount = ocrSignals.filter(o => o.frame_id === fId).length;
            
            // Image source URL
            const imgSrc = `${backendUrl}/uploads/${sessionId}_frame_${frameNum}.jpg`;

            return (
              <button
                key={fId}
                onClick={() => setSelectedFrame(fId)}
                className={`flex-none w-44 bg-[#070708] border rounded-lg overflow-hidden text-left transition-all snap-start ${
                  isSelected 
                    ? 'border-blue-500 shadow-[0_0_12px_rgba(59,130,246,0.25)] ring-1 ring-blue-500/30' 
                    : 'border-[#1f1f23] hover:border-zinc-700'
                }`}
              >
                {/* Visual Thumbnail */}
                <div className="h-24 bg-zinc-950 relative overflow-hidden flex items-center justify-center border-b border-[#1f1f23]">
                  <img
                    src={imgSrc}
                    alt={fId}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      // fallback to placeholder icon if image not found
                      e.target.style.display = 'none';
                      e.target.parentNode.innerHTML = `<div class="flex flex-col items-center gap-1 text-zinc-600"><Compass class="w-6 h-6 animate-spin-slow" /><span class="text-[8px] font-mono">FRAME ${frameNum}</span></div>`;
                    }}
                  />
                  <div className="absolute top-1.5 left-1.5 bg-black/60 backdrop-blur-md px-1.5 py-0.5 rounded text-[8px] font-mono text-zinc-300 font-bold border border-zinc-700/30">
                    FRM {frameNum}
                  </div>
                  <div className={`absolute bottom-1.5 right-1.5 px-1.5 py-0.5 rounded text-[7px] font-mono font-bold border ${
                    tierStr.includes('Tier 2') ? 'bg-purple-950/70 border-purple-500/30 text-purple-400' :
                    tierStr.includes('Tier 1') ? 'bg-blue-950/70 border-blue-500/30 text-blue-400' :
                    'bg-zinc-900/70 border-zinc-700/30 text-zinc-400'
                  }`}>
                    {tierStr}
                  </div>
                </div>

                {/* Info summary */}
                <div className="p-3 space-y-1 font-mono text-[9px]">
                  <div className="flex justify-between items-center text-zinc-400">
                    <span>TIMING</span>
                    <span className="text-white font-bold">{(frameNum / fps).toFixed(2)}s</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-500">
                    <span className="flex items-center gap-1"><MapPin className="w-2.5 h-2.5" /> Landmarks</span>
                    <span className={lCount > 0 ? 'text-blue-400 font-bold' : 'text-zinc-600'}>{lCount}</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-500">
                    <span className="flex items-center gap-1"><Type className="w-2.5 h-2.5" /> OCR Texts</span>
                    <span className={oCount > 0 ? 'text-emerald-400 font-bold' : 'text-zinc-600'}>{oCount}</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Frame Selection Details */}
      {selectedFrame && (
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2 font-mono">
              <Eye className="w-4 h-4 text-emerald-400" /> Frame Signal Analysis: {selectedFrame}
            </h3>
            <span className="font-mono text-[10px] text-zinc-500">
              EST. TIME: <span className="text-white font-bold">{timestampSec}s</span> (FPS: {fps})
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Visual Preview Card */}
            <div className="lg:col-span-4 space-y-3">
              <div className="aspect-video bg-zinc-950 border border-[#1f1f23] rounded-lg overflow-hidden flex items-center justify-center">
                <img
                  src={`${backendUrl}/uploads/${sessionId}_frame_${selectedNum}.jpg`}
                  alt={selectedFrame}
                  className="w-full h-full object-contain"
                  onError={(e) => {
                    e.target.style.display = 'none';
                    e.target.parentNode.innerHTML = `<div class="text-zinc-700 text-center"><Compass class="w-8 h-8 mx-auto animate-spin-slow" /><p class="text-[9px] font-mono mt-1">FRAME IMAGE PREVIEW</p></div>`;
                  }}
                />
              </div>
              <div className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg font-mono text-[9px] text-zinc-500 space-y-1.5">
                <div className="flex justify-between">
                  <span>FRAME INDEX:</span>
                  <span className="text-zinc-300 font-bold">{selectedNum}</span>
                </div>
                <div className="flex justify-between">
                  <span>RESOLVING TIER:</span>
                  <span className="text-zinc-300 font-bold">{getFrameMaxTier(selectedFrame)}</span>
                </div>
                <div className="flex justify-between">
                  <span>TOTAL DETECTIONS:</span>
                  <span className="text-emerald-400 font-bold">{frameLandmarks.length + frameOcr.length}</span>
                </div>
              </div>
            </div>

            {/* Resolved Signals */}
            <div className="lg:col-span-8 space-y-4">
              {/* Landmarks detected */}
              <div className="space-y-2">
                <div className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider">
                  Detections & Landmarks ({frameLandmarks.length})
                </div>
                {frameLandmarks.length > 0 ? (
                  <div className="space-y-2">
                    {frameLandmarks.map((lm, idx) => (
                      <div key={idx} className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg flex justify-between items-start font-mono text-xs">
                        <div className="space-y-1">
                          <div className="font-bold text-zinc-200 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                            {lm.label}
                          </div>
                          <div className="text-[9px] text-zinc-500">
                            Source: <span className="text-zinc-400">{lm.source}</span>
                            {lm.supporting_evidence && ` | ${lm.supporting_evidence}`}
                          </div>
                        </div>
                        <div className="text-right space-y-1">
                          <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-blue-950/40 border border-blue-500/20 text-blue-400 uppercase">
                            CONF: {(lm.score * 100).toFixed(0)}%
                          </span>
                          {lm.lat && lm.lng && (
                            <div className="text-[9px] text-zinc-500 flex items-center justify-end gap-0.5">
                              <MapPin className="w-2.5 h-2.5 text-emerald-400" />
                              {lm.lat.toFixed(4)}, {lm.lng.toFixed(4)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 text-center border border-dashed border-[#1f1f23] rounded-lg text-zinc-600 font-mono text-[10px]">
                    No landmarks resolved on this keyframe
                  </div>
                )}
              </div>

              {/* OCR Signals */}
              <div className="space-y-2">
                <div className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider">
                  Extracted Text & Signage ({frameOcr.length})
                </div>
                {frameOcr.length > 0 ? (
                  <div className="space-y-2">
                    {frameOcr.map((ocr, idx) => (
                      <div key={idx} className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg flex justify-between items-start font-mono text-xs">
                        <div className="space-y-1">
                          <div className="font-bold text-zinc-200 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            "{ocr.text}"
                          </div>
                          <div className="text-[9px] text-zinc-500">
                            Source: <span className="text-zinc-400">{ocr.source}</span>
                          </div>
                        </div>
                        <div className="text-right space-y-1">
                          <span className="text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-950/40 border border-emerald-500/20 text-emerald-400 uppercase">
                            CONF: {(ocr.confidence * 100).toFixed(0)}%
                          </span>
                          <div className="text-[9px] text-zinc-500 uppercase">
                            GEO: <span className={ocr.geocoding_status === 'resolved' ? 'text-emerald-400' : 'text-zinc-600'}>{ocr.geocoding_status}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-3 text-center border border-dashed border-[#1f1f23] rounded-lg text-zinc-600 font-mono text-[10px]">
                    No text or signboards detected on this keyframe
                  </div>
                )}
              </div>

              {/* Candidates generated by this frame */}
              {frameCandidates.length > 0 && (
                <div className="space-y-2">
                  <div className="text-[10px] font-mono font-bold text-zinc-400 uppercase tracking-wider">
                    Geographic Candidates Generated
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {frameCandidates.map((cand, idx) => (
                      <div key={idx} className="p-2.5 bg-zinc-950/40 border border-[#1f1f23] rounded-lg flex justify-between items-center font-mono text-[10px]">
                        <div className="space-y-0.5">
                          <div className="text-zinc-300 font-bold truncate max-w-[140px]">"{cand.raw_signal}"</div>
                          <div className="text-zinc-600 text-[8px] uppercase">Source: {cand.source}</div>
                        </div>
                        <div className="text-right font-semibold text-emerald-400">
                          {cand.lat.toFixed(4)}, {cand.lng.toFixed(4)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
