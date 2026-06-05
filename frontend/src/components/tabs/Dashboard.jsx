import React from 'react';
import { Fingerprint, BarChart3, Cpu, CheckCircle2, Map, Globe, Activity } from 'lucide-react';
import MapWidget from '../visualizations/MapWidget';
import RadarSignals from '../visualizations/RadarSignals';
import TimezoneHistogram from '../visualizations/TimezoneHistogram';

export default function Dashboard({ analysis, loading }) {
  const intPercentage = (val) => {
    if (val === undefined || val === null) return 0;
    if (val <= 1.0) {
      return Math.round(val * 100);
    }
    return Math.round(val);
  };

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-[#0c0c0e] border border-[#1f1f23] p-4 rounded-xl h-28 flex flex-col justify-between">
              <div className="h-3 w-24 bg-zinc-800 rounded"></div>
              <div className="h-6 w-36 bg-zinc-800 rounded"></div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 h-64">
              <div className="h-4 w-32 bg-zinc-800 rounded mb-4"></div>
              <div className="h-36 bg-zinc-800 rounded"></div>
            </div>
          </div>
          <div className="lg:col-span-4 bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 h-64">
            <div className="h-4 w-32 bg-zinc-800 rounded mb-4"></div>
            <div className="h-36 bg-zinc-800 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const signalBreakdown = analysis.location_intelligence?.signal_breakdown || {};
  const timezoneEstimate = analysis.temporal_analysis?.timezone || "UTC +00:00 (Indeterminate)";

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Asset Cryptography Hash", val: analysis.md5 || "N/A", icon: Fingerprint, subtitle: "MD5 Signature" },
          { label: "Target Dimensions", val: analysis.dimensions, icon: BarChart3, subtitle: "Native Resolution" },
          { label: "Device Taxonomy", val: analysis.exif?.camera_model || "Purged", icon: Cpu, subtitle: "EXIF Hardware Model" },
          { label: "Intelligence Verification", val: analysis.location_intelligence ? `${analysis.location_intelligence.country} (${intPercentage(analysis.location_intelligence.confidence)}%)` : "UNVERIFIED", icon: CheckCircle2, color: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5", statusColor: "bg-emerald-400 shadow-[0_0_8px_#10b981]" }
        ].map((item, i) => (
          <div key={i} className={`bg-[#0c0c0e] border border-[#1f1f23] p-4 rounded-xl flex flex-col justify-between h-28 hover:border-zinc-800 transition-colors ${item.color || ''}`}>
            <div className="flex justify-between items-start">
              <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider font-mono">{item.label}</span>
              <item.icon className="w-4 h-4 text-zinc-600" />
            </div>
            <div>
              <div className="text-sm font-bold text-white truncate flex items-center gap-1.5">
                {item.statusColor && <span className={`w-1.5 h-1.5 rounded-full ${item.statusColor}`}></span>}
                {item.val}
              </div>
              <div className="text-[9px] text-zinc-500 font-mono mt-0.5">{item.subtitle}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Unified Analysis Summary Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 space-y-6">
          {/* Map & Environmental Report */}
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2">
                <Map className="w-4 h-4 text-blue-400" /> Environmental Audit & Vision Findings
              </h3>
              <span className="text-[9px] font-mono text-zinc-500 bg-[#121215] px-2 py-0.5 rounded border border-[#1f1f23]">Layer 9</span>
            </div>
            
            {/* Interactive Leaflet Map */}
            <MapWidget analysis={analysis} />
            
            <div className="p-4 bg-[#070708] border border-[#1f1f23] rounded-lg">
              <p className="text-xs text-zinc-400 leading-relaxed font-sans whitespace-pre-wrap">
                {analysis.vision_location_report?.replace(/\*\*/g, '') || "No visual reports generated."}
              </p>
            </div>
          </div>

          {/* Script analysis and priors */}
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2">
                <Globe className="w-4 h-4 text-cyan-400" /> Geospatial Weights & Signal Priors
              </h3>
              <span className="text-[9px] font-mono text-zinc-500 bg-[#121215] px-2 py-0.5 rounded border border-[#1f1f23]">Layer 4</span>
            </div>
            
            {/* Recharts Radar signals */}
            <RadarSignals signalBreakdown={signalBreakdown} />
          </div>
        </div>

        {/* Right side: Quick stats */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6 flex flex-col justify-between h-full">
            <div className="space-y-6">
              <div>
                <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2 mb-4">
                  <Activity className="w-4 h-4 text-red-400" /> Propagation Rate
                </h3>
                <div className="space-y-4">
                  <div className="p-3.5 bg-red-950/15 border border-red-500/20 rounded-lg">
                    <span className="text-[8px] text-zinc-500 uppercase tracking-widest block font-bold mb-1">Velocity Type</span>
                    <span className="text-xs font-bold text-red-400">{analysis.temporal_analysis?.velocity?.split(':')[0] || "ORGANIC"}</span>
                    <span className="text-[10px] text-zinc-500 block leading-relaxed mt-1 font-mono">{analysis.temporal_analysis?.velocity?.split(':').slice(1).join(':') || "Stable audience trace"}</span>
                  </div>
                  <div className="p-3.5 bg-[#121215] border border-[#1f1f23] rounded-lg">
                    <span className="text-[8px] text-zinc-500 uppercase tracking-widest block font-bold mb-1">Initial Seed Window</span>
                    <span className="text-xs font-bold text-zinc-200 font-mono">{analysis.temporal_analysis?.seed_window || "N/A"}</span>
                  </div>
                </div>
              </div>

              {/* Timezone active histogram */}
              <TimezoneHistogram timezoneEstimate={timezoneEstimate} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
