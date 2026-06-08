import React from 'react';
import { Fingerprint, FileText, Info, ShieldCheck, ShieldAlert, BadgeInfo } from 'lucide-react';

export default function EvidencePanel({ analysis, onTerminateSession, onExportPDF, onExportCSV }) {
  const intPercentage = (val) => {
    if (val === undefined || val === null) return 0;
    if (val <= 1.0) {
      return Math.round(val * 100);
    }
    return Math.round(val);
  };

  const getReliabilityColor = (rel) => {
    if (rel >= 0.90) return "text-emerald-400";
    if (rel >= 0.70) return "text-blue-400";
    return "text-zinc-500";
  };

  return (
    <aside className="w-80 border-l border-[#1f1f23] bg-[#0c0c0e] flex flex-col justify-between shrink-0 overflow-y-auto">
      {analysis ? (
        <div className="flex-1 flex flex-col justify-between p-4 space-y-6">
          
          <div className="space-y-6">
            {/* Header / Strict Mode State */}
            <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
              <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest font-mono">Confidence Engine</span>
              {analysis.location_intelligence?.strict_mode !== undefined && (
                <div className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold flex items-center gap-1 ${
                  analysis.location_intelligence.strict_mode 
                    ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                }`}>
                  {analysis.location_intelligence.strict_mode ? <ShieldCheck className="w-2.5 h-2.5" /> : <ShieldAlert className="w-2.5 h-2.5" />}
                  {analysis.location_intelligence.strict_mode ? "STRICT" : "DEMO"}
                </div>
              )}
            </div>
              
            {analysis.location_intelligence && (
              <div className="bg-[#121215] border border-[#1f1f23] rounded-xl p-4 space-y-4">
                {/* Metric Gauge */}
                <div className="flex justify-between items-center border-b border-[#1f1f23] pb-2">
                  <span className="text-xs font-bold text-zinc-200">Ensemble Match</span>
                  <span className="text-xs font-bold text-blue-400 font-mono">{intPercentage(analysis.location_intelligence.confidence)}%</span>
                </div>

                {/* Small inline list */}
                <div className="space-y-2 text-[10px] font-mono">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Suspected Country:</span>
                    <span className="text-zinc-200 font-bold">{analysis.location_intelligence.country}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Zone Offset:</span>
                    <span className="text-zinc-200 font-bold truncate max-w-[130px]">{analysis.location_intelligence.timezone}</span>
                  </div>
                  {analysis.location_intelligence.city && (
                    <div className="flex justify-between">
                      <span className="text-zinc-500">Coordinates Center:</span>
                      <span className="text-zinc-200 font-bold">{analysis.location_intelligence.city}, {analysis.location_intelligence.state}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Active Scoring Layers */}
            {analysis.location_intelligence?.signal_breakdown && (
              <div className="space-y-3">
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest font-mono block">Active Scoring Layers</span>
                <div className="space-y-2">
                  {Object.entries(analysis.location_intelligence.signal_breakdown)
                    .filter(([_, score]) => score > 0)
                    .map(([layer, score]) => (
                      <div key={layer} className="p-2.5 bg-[#121215] border border-[#1f1f23] rounded-lg text-[10px] font-mono space-y-1.5">
                        <div className="flex justify-between font-bold">
                          <span className="uppercase text-zinc-400">{layer.replace("_geocoder", "").replace("_analyzer", "").replace("_llm", "")}</span>
                          <span className="text-blue-400">Score: {score}</span>
                        </div>
                        <div className="h-1 bg-[#070708] rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(100, score * 2.5)}%` }}></div>
                        </div>
                      </div>
                    ))}
                </div>
              </div>
            )}

            {/* Provenance Audit Trail */}
            {analysis.location_intelligence?.evidence_details && analysis.location_intelligence.evidence_details.length > 0 ? (
              <div className="space-y-3">
                <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest font-mono block">Forensic Evidence Provenance</span>
                <div className="bg-[#121215] border border-[#1f1f23] rounded-xl p-3 max-h-60 overflow-y-auto space-y-3 font-mono scrollbar-thin">
                  {analysis.location_intelligence.evidence_details.map((ev, i) => (
                    <div key={i} className="text-[9px] border-b border-[#1f1f23]/50 pb-2 last:border-0 last:pb-0 space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-white font-bold uppercase text-[8px] bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/15">{ev.source.replace("_geocoder", "").replace("_analyzer", "")}</span>
                        <span className={`text-[8px] font-bold ${getReliabilityColor(ev.reliability)}`}>
                          Rel: {Math.round(ev.reliability * 100)}%
                        </span>
                      </div>
                      <div className="text-zinc-500 leading-tight text-[8px] flex flex-col space-y-0.5">
                        <span>Method: <span className="text-zinc-400">{ev.collection_method}</span></span>
                        <span>Type: <span className="text-zinc-400">{ev.source_type}</span></span>
                      </div>
                      <div className="text-zinc-300 leading-relaxed pt-0.5 max-w-[260px] break-all truncate">
                        {typeof ev.value === 'object' ? JSON.stringify(ev.value) : ev.value}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              // Fallback to legacy string audit trail
              analysis.location_intelligence?.evidence?.length > 0 && (
                <div className="space-y-3">
                  <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest font-mono block">Evidence Audit Trail</span>
                  <div className="bg-[#121215] border border-[#1f1f23] rounded-xl p-3.5 max-h-56 overflow-y-auto space-y-2 font-mono scrollbar-thin">
                    {analysis.location_intelligence.evidence.map((ev, i) => (
                      <div key={i} className="text-[9px] leading-relaxed text-zinc-400 flex gap-1.5 items-start">
                        <span className="text-blue-500/70 select-none">›</span>
                        <span>{ev}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            )}
          </div>

          {/* Bottom part: Export actions */}
          <div className="border-t border-[#1f1f23] pt-4 space-y-2">
            <button 
              onClick={onExportPDF}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-mono text-[10px] font-bold py-2 rounded-lg transition-colors uppercase tracking-widest flex items-center justify-center gap-2"
            >
              <FileText className="w-3.5 h-3.5" /> Export PDF Report
            </button>
            <button 
              onClick={onExportCSV}
              className="w-full bg-[#121215] hover:bg-zinc-900 border border-[#1f1f23] text-zinc-400 font-mono text-[10px] py-2 rounded-lg transition-colors uppercase tracking-widest flex items-center justify-center gap-2"
            >
              <FileText className="w-3.5 h-3.5" /> Export CSV Data
            </button>
            <button 
              onClick={onTerminateSession}
              className="w-full bg-[#2d1111]/30 hover:bg-[#2d1111]/60 border border-red-500/20 text-red-400 font-mono text-[10px] py-2 rounded-lg transition-colors uppercase tracking-widest"
            >
              Terminate Session
            </button>
          </div>

        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-zinc-700 font-mono">
          <Info className="w-5 h-5 text-zinc-800 mb-2" />
          <span className="text-[9px] uppercase tracking-wider">No suspect data mapped</span>
        </div>
      )}
    </aside>
  );
}
