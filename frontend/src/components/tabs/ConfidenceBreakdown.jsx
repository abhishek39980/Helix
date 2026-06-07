import React from 'react';
import { ShieldAlert, Activity, CheckSquare } from 'lucide-react';

export default function ConfidenceBreakdown({ confidence, signals }) {
  if (!signals) return null;

  const weights = {
    keyframe_similarity: { label: "Adaptive Keyframes Similarity", weight: 40, color: "bg-blue-500" },
    video_phash: { label: "Aggregate Video pHash Correlation", weight: 25, color: "bg-purple-500" },
    scene_alignment: { label: "Scene Sequence Hamming Distance", weight: 20, color: "bg-emerald-500" },
    duration_similarity: { label: "Temporal Duration Match", weight: 10, color: "bg-amber-500" },
    metadata_similarity: { label: "OCR & Subtitle Text Correlation", weight: 5, color: "bg-rose-500" },
  };

  const getConfidenceLevel = (val) => {
    if (val >= 0.85) return { text: "HIGH FORENSIC CREDIBILITY", style: "text-emerald-400 border-emerald-500/20 bg-emerald-500/5" };
    if (val >= 0.70) return { text: "MEDIUM FORENSIC CREDIBILITY", style: "text-amber-400 border-amber-500/20 bg-amber-500/5" };
    return { text: "PROBABLE CORRELATION (LOW CONFIDENCE)", style: "text-rose-400 border-rose-500/20 bg-rose-500/5" };
  };

  const confLevel = getConfidenceLevel(confidence);

  return (
    <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
      
      {/* Overview Block */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1f1f23] pb-4">
        <div>
          <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Forensic Confidence Audit</h4>
          <p className="text-[10px] text-zinc-500 font-mono mt-0.5">Weighted ensemble matching algorithm breakdown</p>
        </div>
        
        <div className={`px-3 py-1.5 rounded-lg border text-[10px] font-mono font-bold ${confLevel.style} flex items-center gap-1.5`}>
          <ShieldAlert className="w-3.5 h-3.5" />
          {confLevel.text}
        </div>
      </div>

      {/* Main progress list */}
      <div className="space-y-4 font-mono text-xs">
        {Object.entries(signals).map(([key, value]) => {
          const wInfo = weights[key];
          if (!wInfo) return null;

          const percentage = Math.round(value * 100);
          const contribution = Math.round(value * wInfo.weight);

          return (
            <div key={key} className="space-y-1.5">
              <div className="flex justify-between items-center text-[10px]">
                <span className="text-zinc-400 font-bold">{wInfo.label}</span>
                <span className="text-zinc-500">
                  Value: <span className="text-white font-bold">{percentage}%</span> 
                  {` (weight: ${wInfo.weight}%, contrib: ${contribution}%)`}
                </span>
              </div>
              
              {/* Progress gauge container */}
              <div className="h-1.5 bg-[#070708] border border-[#1f1f23] rounded-full overflow-hidden relative">
                <div 
                  className={`h-full ${wInfo.color} rounded-full transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Aggregated Formula block */}
      <div className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg text-[10px] font-mono text-zinc-500 space-y-1">
        <span className="block font-bold text-zinc-400 uppercase">Formula Log:</span>
        <span className="block leading-relaxed">
          Confidence = 0.40(Keyframe) + 0.25(pHash) + 0.20(Scene) + 0.10(Duration) + 0.05(Metadata)
        </span>
      </div>

    </div>
  );
}
