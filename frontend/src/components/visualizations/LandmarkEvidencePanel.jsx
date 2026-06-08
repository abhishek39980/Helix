import React, { useState } from 'react';
import { ShieldCheck, Text, History, Download, MapPin, Search } from 'lucide-react';

export default function LandmarkEvidencePanel({ analysis, backendUrl }) {
  const [activeSubTab, setActiveSubTab] = useState('landmarks');
  const l12 = analysis?.landmark_intelligence;
  if (!l12) return null;

  const landmarks = l12.landmarks_detected || [];
  const ocrSignals = l12.ocr_signals || [];
  const supportingEvidence = l12.supporting_evidence || [];
  const sessionId = analysis.id;

  const getSourceBadge = (src) => {
    switch (src) {
      case 'vision_api':
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-blue-950/40 border border-blue-500/20 text-blue-400">VISION API (T1)</span>;
      case 'serpapi_knowledge_graph':
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-purple-950/40 border border-purple-500/20 text-purple-400">LENS KG (T2)</span>;
      case 'serpapi_visual_match':
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-purple-950/40 border border-purple-500/20 text-purple-400">LENS MATCH (T2)</span>;
      case 'moondream':
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-950/40 border border-amber-500/20 text-amber-400">MOONDREAM (T0)</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-zinc-900 border border-zinc-700 text-zinc-400">{src.toUpperCase()}</span>;
    }
  };

  const getOcrSourceBadge = (src) => {
    if (src === 'vision_api') {
      return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-blue-950/40 border border-blue-500/20 text-blue-400">VISION OCR (T1)</span>;
    }
    return <span className="px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-950/40 border border-amber-500/20 text-amber-400">MOONDREAM (T0)</span>;
  };

  const handleDownloadLandmarks = () => {
    const apiKey = import.meta.env.VITE_API_KEY || "";
    const headers = {};
    if (apiKey) headers["X-API-Key"] = apiKey;
    
    window.open(`${backendUrl}/api/export/${sessionId}/landmark-detections`, '_blank');
  };

  const handleDownloadOcr = () => {
    const apiKey = import.meta.env.VITE_API_KEY || "";
    const headers = {};
    if (apiKey) headers["X-API-Key"] = apiKey;
    
    window.open(`${backendUrl}/api/export/${sessionId}/ocr-signals`, '_blank');
  };

  return (
    <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
      {/* Tab Navigation header */}
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 border-b border-[#1f1f23] pb-3">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveSubTab('landmarks')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all border ${
              activeSubTab === 'landmarks'
                ? 'bg-blue-900/20 border-blue-500/30 text-white'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" /> LANDMARKS ({landmarks.length})
          </button>
          <button
            onClick={() => setActiveSubTab('ocr')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all border ${
              activeSubTab === 'ocr'
                ? 'bg-blue-900/20 border-blue-500/30 text-white'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <Text className="w-3.5 h-3.5" /> OCR SIGNALS ({ocrSignals.length})
          </button>
          <button
            onClick={() => setActiveSubTab('audit')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all border ${
              activeSubTab === 'audit'
                ? 'bg-blue-900/20 border-blue-500/30 text-white'
                : 'border-transparent text-zinc-500 hover:text-zinc-300'
            }`}
          >
            <History className="w-3.5 h-3.5" /> AUDIT TRAIL ({supportingEvidence.length})
          </button>
        </div>

        {/* Download CSV Buttons */}
        <div className="flex gap-2 font-mono">
          {activeSubTab === 'landmarks' && landmarks.length > 0 && (
            <button
              onClick={handleDownloadLandmarks}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#121215] border border-[#1f1f23] hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 text-[10px] rounded-lg transition-colors"
            >
              <Download className="w-3 h-3" /> LANDMARKS CSV
            </button>
          )}
          {activeSubTab === 'ocr' && ocrSignals.length > 0 && (
            <button
              onClick={handleDownloadOcr}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#121215] border border-[#1f1f23] hover:border-zinc-700 text-zinc-400 hover:text-zinc-200 text-[10px] rounded-lg transition-colors"
            >
              <Download className="w-3 h-3" /> OCR CSV
            </button>
          )}
        </div>
      </div>

      {/* Landmarks Tab View */}
      {activeSubTab === 'landmarks' && (
        <div className="overflow-x-auto">
          {landmarks.length > 0 ? (
            <table className="w-full font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#1f1f23] text-zinc-500 text-[10px] uppercase text-left">
                  <th className="pb-3 font-semibold">Label / Landmark</th>
                  <th className="pb-3 font-semibold">Frame ID</th>
                  <th className="pb-3 font-semibold">Tier Source</th>
                  <th className="pb-3 font-semibold">Confidence</th>
                  <th className="pb-3 font-semibold">Coordinates</th>
                  <th className="pb-3 font-semibold">Geocoded</th>
                </tr>
              </thead>
              <tbody>
                {landmarks.map((lm, idx) => (
                  <tr key={idx} className="border-b border-[#1f1f23]/40 hover:bg-zinc-900/10 transition-colors">
                    <td className="py-3.5 pr-3 text-zinc-200 font-bold max-w-[200px] truncate" title={lm.label}>
                      {lm.label}
                    </td>
                    <td className="py-3.5 text-zinc-400 uppercase font-semibold">{lm.frame_id}</td>
                    <td className="py-3.5">{getSourceBadge(lm.source)}</td>
                    <td className="py-3.5">
                      <span className="font-bold text-zinc-300">{(lm.score * 100).toFixed(0)}%</span>
                    </td>
                    <td className="py-3.5 text-zinc-400">
                      {lm.lat && lm.lng ? (
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-emerald-400" />
                          {lm.lat.toFixed(5)}, {lm.lng.toFixed(5)}
                        </span>
                      ) : (
                        <span className="text-zinc-600">—</span>
                      )}
                    </td>
                    <td className="py-3.5">
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                        lm.geocoded
                          ? 'bg-emerald-950/40 border border-emerald-500/20 text-emerald-400'
                          : 'bg-zinc-900 border border-zinc-700 text-zinc-500'
                      }`}>
                        {lm.geocoded ? 'GEOCODED' : 'UNRESOLVED'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-zinc-600 font-mono text-xs border border-dashed border-[#1f1f23] rounded-lg">
              No landmark or geographic visual object signals resolved.
            </div>
          )}
        </div>
      )}

      {/* OCR Tab View */}
      {activeSubTab === 'ocr' && (
        <div className="overflow-x-auto">
          {ocrSignals.length > 0 ? (
            <table className="w-full font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#1f1f23] text-zinc-500 text-[10px] uppercase text-left">
                  <th className="pb-3 font-semibold">Extracted Text Content</th>
                  <th className="pb-3 font-semibold">Frame ID</th>
                  <th className="pb-3 font-semibold">Source</th>
                  <th className="pb-3 font-semibold">Confidence</th>
                  <th className="pb-3 font-semibold">Geocoding Status</th>
                </tr>
              </thead>
              <tbody>
                {ocrSignals.map((ocr, idx) => (
                  <tr key={idx} className="border-b border-[#1f1f23]/40 hover:bg-zinc-900/10 transition-colors">
                    <td className="py-3.5 pr-3 text-zinc-200 font-bold max-w-[300px] truncate" title={ocr.text}>
                      "{ocr.text}"
                    </td>
                    <td className="py-3.5 text-zinc-400 uppercase font-semibold">{ocr.frame_id}</td>
                    <td className="py-3.5">{getOcrSourceBadge(ocr.source)}</td>
                    <td className="py-3.5">
                      <span className="font-bold text-zinc-300">{(ocr.confidence * 100).toFixed(0)}%</span>
                    </td>
                    <td className="py-3.5">
                      <span className={`px-1.5 py-0.5 rounded text-[8px] font-bold ${
                        ocr.geocoding_status === 'resolved'
                          ? 'bg-emerald-950/40 border border-emerald-500/20 text-emerald-400'
                          : ocr.geocoding_status === 'skipped'
                          ? 'bg-zinc-900 border border-zinc-700 text-zinc-500'
                          : 'bg-amber-950/40 border border-amber-500/20 text-amber-400'
                      }`}>
                        {ocr.geocoding_status?.toUpperCase() || 'PENDING'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-8 text-center text-zinc-600 font-mono text-xs border border-dashed border-[#1f1f23] rounded-lg">
              No textual or billboard signaling resolved on video keyframes.
            </div>
          )}
        </div>
      )}

      {/* Audit Trail Tab View */}
      {activeSubTab === 'audit' && (
        <div className="space-y-4">
          {supportingEvidence.length > 0 ? (
            <div className="space-y-3">
              {supportingEvidence.map((log, idx) => {
                let badgeColor = 'bg-zinc-900 border-zinc-700 text-zinc-400';
                if (log.tier === 0) badgeColor = 'bg-amber-950/30 border-amber-500/15 text-amber-400';
                if (log.tier === 1) badgeColor = 'bg-blue-950/30 border-blue-500/15 text-blue-400';
                if (log.tier === 2) badgeColor = 'bg-purple-950/30 border-purple-500/15 text-purple-400';
                if (log.tier === 3) badgeColor = 'bg-emerald-950/30 border-emerald-500/15 text-emerald-400';

                return (
                  <div 
                    key={idx} 
                    className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg flex items-start gap-4 font-mono text-xs hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex-none flex flex-col items-center">
                      <span className={`px-2 py-0.5 rounded border text-[8px] font-bold ${badgeColor}`}>
                        TIER {log.tier}
                      </span>
                      <span className="text-[8px] text-zinc-600 mt-1 uppercase font-semibold">{log.frame_id}</span>
                    </div>
                    
                    <div className="space-y-1">
                      <div className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider flex items-center gap-1.5">
                        <Search className="w-3 h-3 text-zinc-600" />
                        {log.evidence_type?.replace(/_/g, ' ')}
                      </div>
                      <div className="text-zinc-300 leading-relaxed text-[11px]">{log.description}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="py-8 text-center text-zinc-600 font-mono text-xs border border-dashed border-[#1f1f23] rounded-lg">
              No visual location intelligence audit trace logs detected.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
