import React from 'react';
import { ExternalLink, ShieldCheck, AlertCircle } from 'lucide-react';

export default function MatchGrid({ occurrences }) {
  if (!occurrences || occurrences.length === 0) {
    return (
      <div className="p-8 text-center border border-dashed border-[#1f1f23] rounded-xl text-zinc-500 text-xs font-mono">
        No dissemination targets identified in global repositories.
      </div>
    );
  }

  const getPlatformStyle = (platform) => {
    switch (platform?.toLowerCase()) {
      case 'x (twitter)':
      case 'twitter':
        return 'bg-zinc-900 border-zinc-700 text-zinc-300';
      case 'telegram':
        return 'bg-sky-950/40 border-sky-500/20 text-sky-400';
      case 'reddit':
        return 'bg-orange-950/40 border-orange-500/20 text-orange-400';
      case 'tiktok':
        return 'bg-rose-950/40 border-rose-500/20 text-rose-400';
      default:
        return 'bg-zinc-800/40 border-[#1f1f23] text-zinc-400';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.90) return 'text-emerald-400 bg-emerald-500/5 border-emerald-500/20';
    if (score >= 0.75) return 'text-amber-400 bg-amber-500/5 border-amber-500/20';
    return 'text-rose-400 bg-rose-500/5 border-rose-500/20';
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {occurrences.map((occ, idx) => (
        <div key={idx} className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4 flex flex-col justify-between hover:border-zinc-800 transition-colors space-y-3 relative overflow-hidden group">
          
          {/* Top Bar */}
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${getPlatformStyle(occ.platform)}`}>
                {occ.platform}
              </span>
              <span className="text-[10px] text-zinc-500 font-mono">
                {occ.username || 'anonymous'}
              </span>
            </div>
            
            <a 
              href={occ.url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="p-1 rounded bg-[#121215] border border-[#1f1f23] text-zinc-500 hover:text-white transition-colors"
            >
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>

          {/* Caption / Snippet */}
          <div className="text-[11px] text-zinc-400 leading-relaxed font-sans line-clamp-2">
            {occ.caption || 'No caption text captured.'}
          </div>

          {/* Bottom Info Row */}
          <div className="flex justify-between items-center border-t border-[#121215] pt-3 text-[10px] font-mono">
            <div className="text-zinc-600">
              {occ.timestamp ? new Date(occ.timestamp).toLocaleDateString() : 'Unknown Time'}
            </div>
            
            <div className="flex items-center gap-1.5">
              <span className={`px-2 py-0.5 rounded border text-[9px] font-bold uppercase ${getScoreColor(occ.similarity_score)}`}>
                SIM: {Math.round(occ.similarity_score * 100)}%
              </span>
              <span className="text-zinc-400 bg-[#121215] border border-[#1f1f23] px-2 py-0.5 rounded text-[9px] uppercase">
                {occ.mutation_type || 'Unknown'}
              </span>
            </div>
          </div>

          {/* Highlight logo watermark match */}
          {occ.logo && occ.logo !== 'Unknown' && (
            <div className="absolute right-0 bottom-0 left-0 bg-blue-950/20 border-t border-blue-500/10 px-4 py-1 text-[8px] font-mono text-blue-400 flex items-center gap-1">
              <ShieldCheck className="w-2.5 h-2.5" />
              <span>Watermark detected: {occ.logo} (conf={Math.round(occ.logo_confidence * 100)}%)</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
