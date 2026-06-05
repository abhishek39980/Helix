import React from 'react';
import { Fingerprint, BadgeCheck, Link, Clock, Map, Shield, MessageSquare, Share2 } from 'lucide-react';

export default function ProfileIntel({ 
  analysis, 
  textAnalysis, 
  captionInput, 
  setCaptionInput, 
  onLinguisticAnalyze, 
  textLoading 
}) {
  const intPercentage = (val) => {
    if (val === undefined || val === null) return 0;
    if (val <= 1.0) {
      return Math.round(val * 100);
    }
    return Math.round(val);
  };

  if (!analysis) return null;

  const sourceProfile = analysis.source_profile || {};
  
  const liveProfileDetails = {
    username: sourceProfile.username || "Local Node",
    displayName: sourceProfile.display_name || "Local Node",
    bio: sourceProfile.description || "No description provided.",
    website: sourceProfile.website || "N/A",
    accountAge: sourceProfile.join_date ? `Joined: ${sourceProfile.join_date}` : "N/A",
    location: sourceProfile.location || "Unknown",
    tweetSource: sourceProfile.tweet_source || "local",
    riskIndicators: [
      {
        name: "Location Discrepancy",
        level: analysis.location_intelligence?.country ? "ANALYZED" : "UNVERIFIED",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      },
      {
        name: "Bot Probability",
        level: textAnalysis?.bot_probability || "UNKNOWN",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      },
      {
        name: "Account Source",
        level: (sourceProfile.tweet_source || "local").toUpperCase(),
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      },
      {
        name: "Linguistic Sweep",
        level: textAnalysis ? "COMPLETE" : "PENDING",
        color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
      }
    ]
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* Top profile banner */}
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 flex flex-col md:flex-row gap-6 items-start md:items-center">
        <div className="w-16 h-16 rounded-xl bg-blue-950 border border-blue-500/20 flex items-center justify-center shrink-0">
          <Fingerprint className="w-6 h-6 text-blue-400" />
        </div>
        <div className="flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-white">{liveProfileDetails.displayName}</h3>
            {liveProfileDetails.displayName !== 'Local Node' && <BadgeCheck className="w-4.5 h-4.5 text-blue-400" />}
            <span className="text-xs font-mono text-zinc-500">{liveProfileDetails.username}</span>
          </div>
          <p className="text-xs text-zinc-400 leading-relaxed font-sans max-w-xl">
            {liveProfileDetails.bio}
          </p>
          <div className="flex flex-wrap gap-4 text-[10px] font-mono text-zinc-500">
            <span className="flex items-center gap-1"><Link className="w-3 h-3" /> {liveProfileDetails.website}</span>
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {liveProfileDetails.accountAge}</span>
            {liveProfileDetails.location !== 'Unknown' && (
              <span className="flex items-center gap-1"><Map className="w-3 h-3" /> {liveProfileDetails.location}</span>
            )}
          </div>
        </div>

        {analysis.location_intelligence && (
          <div className="w-full md:w-auto p-4 rounded-xl bg-blue-900/10 border border-blue-500/20 text-center flex flex-col items-center shrink-0">
            <span className="text-[9px] text-zinc-500 uppercase tracking-widest font-mono">Reliability Rating</span>
            <span className="text-2xl font-bold text-blue-400 font-mono mt-1">{intPercentage(analysis.location_intelligence.confidence)}%</span>
          </div>
        )}
      </div>

      {/* Risk indices & sweep tools */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Risk factors */}
        <div className="lg:col-span-2 bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
          <h4 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-blue-400" /> Risk and Spoofing Assessments
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {liveProfileDetails.riskIndicators.map((risk, idx) => (
              <div key={idx} className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                <span className="text-xs text-zinc-400 font-mono">{risk.name}</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider font-mono ${risk.color}`}>
                  {risk.level}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Linguistic Sweep Gateway */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
          <h4 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-blue-400" /> Linguistic Sweep Analyzer
          </h4>
          
          <div className="space-y-3">
            <textarea 
              value={captionInput}
              onChange={(e) => setCaptionInput(e.target.value)}
              placeholder="Enter suspect caption metadata..."
              className="w-full h-20 bg-[#121215] border border-[#1f1f23] rounded-lg p-2.5 text-xs text-zinc-300 placeholder-zinc-700 focus:outline-none focus:border-blue-500/50 resize-none font-mono"
            />
            <button 
              onClick={onLinguisticAnalyze} 
              disabled={textLoading || !captionInput}
              className="w-full bg-zinc-800 hover:bg-zinc-700 text-white font-mono text-[10px] py-2 rounded font-bold transition-colors uppercase tracking-widest disabled:opacity-20"
            >
              {textLoading ? "SWEPT PROCESS ACTIVE..." : "RUN NARRATIVE PARSING"}
            </button>
          </div>

          {textAnalysis && (
            <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg space-y-2 text-[10px] font-mono">
              <div className="flex justify-between items-center border-b border-[#1f1f23] pb-1.5">
                <span className="text-zinc-500">Origin Language</span>
                <span className="text-white font-bold">{textAnalysis.language_origin}</span>
              </div>
              <div className="flex justify-between items-center border-b border-[#1f1f23] pb-1.5">
                <span className="text-zinc-500">Narrative Typology</span>
                <span className="text-white font-bold text-right">{textAnalysis.narrative_category}</span>
              </div>
              <div>
                <span className="text-zinc-500 block mb-1">Structural Notes</span>
                <span className="text-zinc-400 italic font-sans">"{textAnalysis.translation_artifacts}"</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Advanced Forensics: Social Graph & Cross-Platform Resolution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        
        {/* 1. Cross-Platform Identity Resolution */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
          <h4 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <Fingerprint className="w-4 h-4 text-blue-400" /> Cross-Platform Identity Resolution
          </h4>
          <div className="space-y-3">
            {analysis.location_intelligence?.cross_platform?.resolved_profiles ? (
              analysis.location_intelligence.cross_platform.resolved_profiles.map((p, idx) => (
                <div key={idx} className="p-3.5 bg-[#121215] border border-[#1f1f23] rounded-lg flex flex-col gap-2">
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider font-mono ${
                        p.status === 'resolved' 
                          ? 'text-blue-400 bg-blue-500/10 border-blue-500/20' 
                          : 'text-zinc-500 bg-zinc-900 border-zinc-800'
                      }`}>
                        {p.platform}
                      </span>
                      <span className="text-xs font-bold text-zinc-300 font-mono">@{p.username}</span>
                    </div>
                    {p.status === 'resolved' ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-400 hover:underline font-mono">
                        VIEW PROFILE →
                      </a>
                    ) : (
                      <span className="text-[9px] text-zinc-600 font-mono">NOT FOUND</span>
                    )}
                  </div>
                  {p.status === 'resolved' && (
                    <div className="text-[10px] space-y-1.5 font-mono border-t border-[#1f1f23]/60 pt-2 mt-1">
                      {p.location && (
                        <div className="flex justify-between">
                          <span className="text-zinc-500">Resolved Location:</span>
                          <span className="text-emerald-400 font-bold">{p.location}</span>
                        </div>
                      )}
                      {p.bio && (
                        <div className="text-zinc-400 text-[9px] leading-relaxed italic font-sans">
                          "{p.bio}"
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-xs text-zinc-500 font-mono p-4 text-center">No cross-platform identity verification data is active.</div>
            )}
          </div>
        </div>

        {/* 2. Social Graph Geographic Clustering */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
          <h4 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <Share2 className="w-4 h-4 text-blue-400" /> Geographic Clustering Network
          </h4>
          
          <div className="space-y-4">
            <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1 scrollbar-thin">
              {analysis.location_intelligence?.social_graph?.connections ? (
                analysis.location_intelligence.social_graph.connections.map((c, idx) => (
                  <div key={idx} className="p-2.5 bg-[#121215] border border-[#1f1f23] rounded-lg text-[10px] font-mono space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-zinc-300">@{c.username}</span>
                      <span className="text-zinc-500">Weight: <span className="text-blue-400 font-bold">{c.weight}</span></span>
                    </div>
                    <div className="flex justify-between items-center text-[9px] border-t border-[#1f1f23]/50 pt-1.5 text-zinc-500">
                      <span>Signal Vector:</span>
                      <span className="text-zinc-300">{c.location || "Indeterminate"}</span>
                    </div>
                    <div className="h-1 bg-[#070708] rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${Math.min(100, c.weight * 2.5)}%` }}></div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-xs text-zinc-500 font-mono p-4 text-center">No social connections traced.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
