import React from 'react';
import { Clock, ZoomIn, ZoomOut } from 'lucide-react';

export default function TimelineAnalyser({ 
  analysis, 
  selectedTimelineEvent, 
  setSelectedTimelineEvent 
}) {
  if (!analysis) return null;

  // Timeline events derived from live mutation tree
  const timelineEvents = (analysis.mutation_tree?.variants || []).map((v, idx) => ({
    time: v.timestamp || "Unknown",
    title: v.mutation || `Node ${idx + 1}`,
    platform: v.platform || "Unknown",
    account: v.account || "Unknown",
    desc: `${v.platform} — ${v.mutation}`,
    type: v.id === 'current_uploaded' ? 'source' : v.id === 'node_root' ? 'repost' : 'amp'
  }));

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
        <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
          <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-400" /> Interactive Chronological Event Timeline
          </h3>
          <div className="flex items-center gap-1.5">
            <button className="p-1 rounded bg-[#121215] border border-[#1f1f23] text-zinc-500 hover:text-zinc-300"><ZoomIn className="w-3.5 h-3.5" /></button>
            <button className="p-1 rounded bg-[#121215] border border-[#1f1f23] text-zinc-500 hover:text-zinc-300"><ZoomOut className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {/* Interactive SVG timeline */}
        <div className="relative py-8 px-4 bg-[#070708] border border-[#1f1f23] rounded-lg overflow-x-auto min-h-[160px]">
          <svg className="w-full min-w-[700px] h-24" style={{ overflow: 'visible' }}>
            {/* Main Timeline bar */}
            <line x1="5%" y1="50" x2="95%" y2="50" stroke="#1f1f23" strokeWidth="4" />
            <line x1="5%" y1="50" x2="65%" y2="50" stroke="#2563eb" strokeWidth="4" />

            {timelineEvents.map((ev, idx) => {
              const xVal = 5 + (idx * 30); // distribute
              const isSelected = selectedTimelineEvent === idx;
              return (
                <g key={idx} className="cursor-pointer" onClick={() => setSelectedTimelineEvent(idx)}>
                  <circle 
                    cx={`${xVal}%`} 
                    cy="50" 
                    r={isSelected ? "10" : "7"} 
                    fill={ev.type === 'source' ? "#3b82f6" : ev.type === 'spike' ? "#ef4444" : "#10b981"} 
                    stroke={isSelected ? "#fff" : "transparent"}
                    strokeWidth="2.5"
                    className="transition-all duration-300 hover:r-11"
                  />
                  <text 
                    x={`${xVal}%`} 
                    y="25" 
                    textAnchor="middle" 
                    fill="#fff" 
                    className="text-[9px] font-mono font-bold"
                  >
                    {ev.time}
                  </text>
                  <text 
                    x={`${xVal}%`} 
                    y="80" 
                    textAnchor="middle" 
                    fill={isSelected ? "#3b82f6" : "#6b7280"} 
                    className="text-[8px] tracking-tight uppercase"
                  >
                    {ev.title.substring(0, 15)}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Detailed timeline card based on selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {timelineEvents.map((ev, idx) => (
            <div 
              key={idx} 
              onClick={() => setSelectedTimelineEvent(idx)}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                selectedTimelineEvent === idx 
                  ? 'bg-blue-900/10 border-blue-500/50 shadow-md shadow-blue-500/5' 
                  : 'bg-[#121215] border-[#1f1f23] hover:border-zinc-800'
              }`}
            >
              <div className="flex justify-between items-center mb-2">
                <span className="text-[9px] font-mono text-zinc-500">{ev.time}</span>
                <span className={`px-1.5 py-0.5 rounded text-[8px] font-mono uppercase font-bold ${
                  ev.type === 'source' ? 'text-blue-400 bg-blue-500/10' :
                  ev.type === 'spike' ? 'text-red-400 bg-red-500/10' :
                  'text-emerald-400 bg-emerald-500/10'
                }`}>{ev.type}</span>
              </div>
              <h4 className="text-xs font-bold text-white uppercase">{ev.title}</h4>
              <div className="text-[10px] text-zinc-500 font-mono mt-1">Publisher: {ev.account} ({ev.platform})</div>
              <p className="text-[11px] text-zinc-400 mt-2 font-sans leading-relaxed">{ev.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
