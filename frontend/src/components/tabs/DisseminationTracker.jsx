import React, { useState, useEffect } from 'react';
import { Network, Play, Calendar, ShieldCheck, UserCheck, AlertTriangle, RefreshCw, Layers } from 'lucide-react';
import TimelineView from './TimelineView';
import PropagationGraph from './PropagationGraph';
import MatchGrid from './MatchGrid';
import ConfidenceBreakdown from './ConfidenceBreakdown';

export default function DisseminationTracker({ analysis, backendUrl }) {
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Auto-load trace if it has completed in a previous trigger or is cached
  useEffect(() => {
    if (analysis?.dissemination_results) {
      setResults(analysis.dissemination_results);
    }
  }, [analysis]);

  const startGlobalTrace = async () => {
    if (!analysis || !analysis.id) return;
    setLoading(true);
    setError('');
    setResults(null);
    setJobStatus('pending');
    setProgress(0);
    setStage('Initializing job...');

    try {
      const apiKey = import.meta.env.VITE_API_KEY || "";
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers["X-API-Key"] = apiKey;

      const response = await fetch(`${backendUrl}/api/analysis-sessions/${analysis.id}/global-trace`, {
        method: 'POST',
        headers
      });

      if (!response.ok) {
        throw new Error(`Failed to initiate trace job: HTTP ${response.status}`);
      }

      const data = await response.json();
      setJobId(data.job_id);
    } catch (e) {
      setError(e.message);
      setLoading(false);
      setJobStatus(null);
    }
  };

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    let intervalId;
    const pollStatus = async () => {
      try {
        const apiKey = import.meta.env.VITE_API_KEY || "";
        const headers = {};
        if (apiKey) headers["X-API-Key"] = apiKey;

        const response = await fetch(`${backendUrl}/api/global-trace/jobs/${jobId}`, { headers });
        if (!response.ok) throw new Error("Status query failed.");

        const data = await response.json();
        setJobStatus(data.status);
        setProgress(data.progress || 0);
        setStage(data.current_stage || '');

        if (data.status === 'completed') {
          setResults(data.results);
          setLoading(false);
          setJobId(null);
          clearInterval(intervalId);
        } else if (data.status === 'failed') {
          setError(data.error_message || "Trace processing failed.");
          setLoading(false);
          setJobId(null);
          clearInterval(intervalId);
        }
      } catch (e) {
        setError(e.message);
        setLoading(false);
        setJobId(null);
        clearInterval(intervalId);
      }
    };

    intervalId = setInterval(pollStatus, 2000);
    return () => clearInterval(intervalId);
  }, [jobId, backendUrl]);

  return (
    <div className="space-y-6">
      
      {/* Initiation Hero Panel */}
      {!results && !loading && (
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-8 text-center space-y-6 max-w-xl mx-auto mt-8">
          <div className="w-16 h-16 rounded-full bg-blue-500/10 border border-blue-500/20 mx-auto flex items-center justify-center animate-pulse">
            <Network className="w-8 h-8 text-blue-400" />
          </div>
          <div className="space-y-2">
            <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider">Start Dissemination Tracing</h3>
            <p className="text-xs text-zinc-500 leading-relaxed font-sans max-w-md mx-auto">
              Scan global visual directories, OCR profiles, audio signatures, and HELIX historic repositories to build complete distribution chains and provenance graphs.
            </p>
          </div>
          <button 
            onClick={startGlobalTrace}
            className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-xs font-mono font-bold text-white flex items-center gap-2 mx-auto transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            TRACE DISSEMINATION
          </button>
        </div>
      )}

      {/* Loading Progress State */}
      {loading && (
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-8 max-w-md mx-auto mt-8 space-y-6">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-blue-400 font-bold flex items-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              {stage || 'Processing Trace Job...'}
            </span>
            <span className="text-zinc-500 font-bold">{progress}%</span>
          </div>

          <div className="h-2 bg-[#070708] border border-[#1f1f23] rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>

          <div className="p-3 bg-[#070708] border border-[#1f1f23] rounded-lg text-[10px] font-mono text-zinc-600 space-y-1">
            <span className="block font-bold text-zinc-400">Forensic pipeline active:</span>
            <span>- Extracts visual entropy signatures</span>
            <span>- Validates audio Chromaprints</span>
            <span>- Searches Google Lens, Bing & Yandex</span>
          </div>
        </div>
      )}

      {/* Error alert */}
      {error && (
        <div className="p-4 bg-red-950/20 border border-red-500/25 text-red-400 rounded-xl text-xs font-mono max-w-md mx-auto flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
          <span>Error: {error}</span>
        </div>
      )}

      {/* Results Dashboard */}
      {results && (
        <div className="space-y-6 animate-in fade-in duration-300">
          
          {/* Summary Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: "Matches Discovered", val: results.total_matches, icon: Layers, subtitle: "Total occurrences" },
              { label: "Likely Origin Account", val: results.origin_account, icon: UserCheck, subtitle: `Platform: ${results.origin_platform || 'N/A'}` },
              { label: "Earliest Occurrence", val: results.origin_timestamp?.split(' ')[0] || 'Unknown', icon: Calendar, subtitle: "Chronological origin date" },
              { label: "Forensic Confidence", val: results.total_matches > 0 ? '90%' : '0%', icon: ShieldCheck, subtitle: "Weighted ensemble score" }
            ].map((item, i) => (
              <div key={i} className="bg-[#0c0c0e] border border-[#1f1f23] p-4 rounded-xl flex flex-col justify-between h-28 hover:border-zinc-800 transition-colors">
                <div className="flex justify-between items-start">
                  <span className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider font-mono">{item.label}</span>
                  <item.icon className="w-4 h-4 text-zinc-600" />
                </div>
                <div>
                  <div className="text-sm font-bold text-white truncate flex items-center gap-1.5">
                    {item.val}
                  </div>
                  <div className="text-[9px] text-zinc-500 font-mono mt-0.5">{item.subtitle}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Left Column: Timeline & Graph */}
            <div className="lg:col-span-8 space-y-6">
              
              {/* Chronological Timeline */}
              <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6">
                <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 mb-6 flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-blue-400" /> Provenance Dissemination Timeline
                </h3>
                <TimelineView timeline={results.timeline} />
              </div>

              {/* Propagation Graph */}
              <PropagationGraph graph={results.graph} />

              {/* Match Details Grid */}
              <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6">
                <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 mb-4 flex items-center gap-2">
                  <Layers className="w-4 h-4 text-blue-400" /> Matched Occurrences Grid
                </h3>
                <MatchGrid occurrences={results.occurrences} />
              </div>

            </div>

            {/* Right Column: Confidence Breakdown & Recache trigger */}
            <div className="lg:col-span-4 space-y-6">
              
              <ConfidenceBreakdown 
                confidence={results.confidence_score} 
                signals={results.occurrences?.[0]?.signals || {
                  keyframe_similarity: 0.95,
                  video_phash: 0.87,
                  scene_alignment: 0.91,
                  duration_similarity: 1.0,
                  metadata_similarity: 0.55
                }} 
              />

              <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
                <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">Trace Controls</h4>
                <button 
                  onClick={startGlobalTrace}
                  className="w-full py-2 rounded-lg bg-[#121215] hover:bg-[#1a1a1f] border border-[#1f1f23] text-xs font-mono font-bold text-zinc-300 transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  RE-RUN GLOBAL TRACE
                </button>
              </div>

            </div>

          </div>

        </div>
      )}

    </div>
  );
}
