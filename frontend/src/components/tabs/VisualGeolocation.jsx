import React from 'react';
import { ShieldAlert, Compass, Globe, Navigation, Award, Layers } from 'lucide-react';
import ClusterMap from '../visualizations/ClusterMap';
import LandmarkTimeline from '../visualizations/LandmarkTimeline';
import LandmarkEvidencePanel from '../visualizations/LandmarkEvidencePanel';

export default function VisualGeolocation({ analysis, backendUrl }) {
  if (!analysis) return null;

  const l12 = analysis.landmark_intelligence;

  // Render unresolved / no-data state
  if (!l12 || l12.status === 'unresolved') {
    return (
      <div className="space-y-6 animate-in fade-in duration-300">
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-8 max-w-2xl mx-auto text-center space-y-6 font-mono">
          <div className="w-16 h-16 rounded-full bg-amber-500/10 border border-amber-500/20 mx-auto flex items-center justify-center animate-pulse">
            <ShieldAlert className="w-8 h-8 text-amber-500" />
          </div>
          <div className="space-y-2">
            <h2 className="text-sm font-bold text-white uppercase tracking-widest">
              Visual Location Intelligence: Unresolved
            </h2>
            <p className="text-xs text-zinc-500 leading-relaxed max-w-md mx-auto">
              {l12?.reason === 'insufficient evidence' 
                ? "The forensic engine could not confidently resolve a coordinate location. There were not enough distinct landmarks, text, or visual search matches on keyframes." 
                : l12?.reason === 'conflicting evidence'
                ? "Location intelligence aborted due to conflicting evidence. Multi-cluster outputs yielded near-identical weights in disparate locations, preventing a safe consensus."
                : "No visual geolocational data mapped for this session. Please upload a media file containing visual evidence."}
            </p>
          </div>

          <div className="pt-4 border-t border-[#1f1f23] text-[10px] text-zinc-600 flex justify-center gap-6">
            <div>TIERS ACTIVE: T0 / T1 / T2</div>
            <div>STATUS: CONSTRAINED</div>
          </div>
        </div>
      </div>
    );
  }

  const estLoc = l12.estimated_location || {};
  const coords = estLoc.coordinates || {};
  const conf = l12.confidence || {};
  const stats = l12.pipeline_stats || {};

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* Overview Dashboard Header Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Estimated Address */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4.5 flex gap-4 items-center">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center shrink-0">
            <Globe className="w-5 h-5 text-blue-400" />
          </div>
          <div className="font-mono min-w-0">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest block">Suspected Location</span>
            <span className="text-xs font-bold text-white truncate block mt-1">
              {estLoc.city}, {estLoc.country}
            </span>
            <span className="text-[9px] text-zinc-500 truncate block mt-0.5">
              Region: {estLoc.region || 'Unknown'}
            </span>
          </div>
        </div>

        {/* Coords & Error Circle */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4.5 flex gap-4 items-center">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center shrink-0">
            <Navigation className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="font-mono">
            <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest block">Centroid Coordinates</span>
            <span className="text-xs font-bold text-emerald-400 block mt-1">
              {coords.lat?.toFixed(5)}, {coords.lng?.toFixed(5)}
            </span>
            <span className="text-[9px] text-zinc-500 block mt-0.5">
              Radius: ±{coords.accuracy_radius_km?.toFixed(1)} km
            </span>
          </div>
        </div>

        {/* Combined Confidence Gauge */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4.5 flex gap-4 items-center">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center shrink-0">
            <Award className="w-5 h-5 text-purple-400" />
          </div>
          <div className="font-mono flex-1">
            <div className="flex justify-between items-center">
              <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Confidence</span>
              <span className="text-xs font-bold text-purple-400">{(conf.overall * 100).toFixed(0)}%</span>
            </div>
            <div className="h-1.5 bg-[#070708] rounded-full overflow-hidden mt-1.5">
              <div 
                className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full" 
                style={{ width: `${conf.overall * 100}%` }}
              ></div>
            </div>
            <span className="text-[8px] text-zinc-600 block mt-1 uppercase">
              Triangulated consensus
            </span>
          </div>
        </div>

        {/* Budget & Frame stats */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4.5 flex gap-4 items-center">
          <div className="w-10 h-10 rounded-lg bg-zinc-800 border border-zinc-700/50 flex items-center justify-center shrink-0">
            <Layers className="w-5 h-5 text-zinc-400" />
          </div>
          <div className="font-mono text-[9px] text-zinc-400 flex-1 space-y-0.5">
            <span className="font-bold text-zinc-500 uppercase tracking-widest block mb-1">Deduplication & Budget</span>
            <div className="flex justify-between">
              <span>Processed:</span>
              <span className="text-white font-bold">{stats.total_frames_extracted || 1} frames</span>
            </div>
            <div className="flex justify-between">
              <span>Tier 1 (Vision):</span>
              <span className="text-blue-400 font-bold">{stats.frames_tier1_resolved || 0} resolved</span>
            </div>
            <div className="flex justify-between">
              <span>Tier 2 (Lens):</span>
              <span className="text-purple-400 font-bold">{stats.frames_tier2_resolved || 0} resolved</span>
            </div>
          </div>
        </div>

      </div>

      {/* Main Grid: Leaflet Map & Details */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Col: The Cluster Map */}
        <div className="lg:col-span-8 space-y-6">
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2 font-mono">
              <Compass className="w-4 h-4 text-emerald-400" /> Spatial Cluster Consensus Map
            </h3>
            <ClusterMap 
              estimatedLocation={estLoc}
              candidateLocations={l12.candidate_locations}
              clusterSummary={l12.cluster_summary}
            />
          </div>

          {/* Horizontal Keyframe Timeline */}
          <LandmarkTimeline 
            analysis={analysis}
            backendUrl={backendUrl}
          />
        </div>

        {/* Right Col: Evidence Tables */}
        <div className="lg:col-span-4 space-y-6">
          <LandmarkEvidencePanel 
            analysis={analysis}
            backendUrl={backendUrl}
          />
        </div>

      </div>

    </div>
  );
}
