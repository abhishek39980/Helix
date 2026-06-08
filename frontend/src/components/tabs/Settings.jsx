import React, { useEffect, useState } from 'react';
import { Settings as SettingsIcon, ShieldCheck, ShieldAlert, Cpu, Activity } from 'lucide-react';

export default function Settings({ backendUrl }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const apiKey = import.meta.env.VITE_API_KEY || "";
        const headers = {};
        if (apiKey) headers["X-API-Key"] = apiKey;

        const res = await fetch(`${backendUrl}/api/settings`, { headers });
        if (res.ok) {
          const data = await res.json();
          setConfig(data);
        }
      } catch (err) {
        console.error("Failed to fetch pipeline settings:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, [backendUrl]);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      
      {/* Strict Mode Banner */}
      <div className={`p-4 rounded-xl border flex items-center justify-between font-mono text-xs ${
        config?.strict_mode 
          ? "bg-blue-500/5 border-blue-500/20 text-blue-400"
          : "bg-amber-500/5 border-amber-500/20 text-amber-400"
      }`}>
        <div className="flex items-center gap-3">
          {config?.strict_mode ? <ShieldCheck className="w-6 h-6" /> : <ShieldAlert className="w-6 h-6" />}
          <div>
            <h4 className="font-bold text-white uppercase tracking-wider">Strict Forensic Mode is {config?.strict_mode ? "Active" : "Inactive"}</h4>
            <p className="text-[10px] text-zinc-500 mt-1">
              {config?.strict_mode 
                ? "Fabricated evidence fallbacks, simulated OCR values, and pseudo-posts are strictly prohibited. Failed acquisitions resolve to explicit failure states."
                : "Simulation mode is active. Fallback mock videos and OCR strings are permitted for demonstration purposes."}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* API Configurations */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
          <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <SettingsIcon className="w-4 h-4 text-blue-400" /> Pipeline Configuration Settings
          </h3>
          <div className="space-y-4 text-xs font-mono">
            <div className="space-y-1">
              <label className="text-zinc-500 block uppercase text-[9px] font-bold">API Ingress Target Host</label>
              <input type="text" readOnly value={backendUrl} className="w-full bg-[#121215] border border-[#1f1f23] rounded p-2 text-zinc-300" />
            </div>
            <div className="space-y-1">
              <label className="text-zinc-500 block uppercase text-[9px] font-bold">OpenCage Geocoder</label>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${config?.opencage_configured ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800 text-zinc-400'}`}>
                {config?.opencage_configured ? 'Configured' : 'Not Configured (Using public OSM fallback)'}
              </span>
            </div>
            <div className="space-y-1">
              <label className="text-zinc-500 block uppercase text-[9px] font-bold">Serper OSINT engine</label>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${config?.serper_configured ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                {config?.serper_configured ? 'API Connected' : 'Missing API Key (Serper disabled)'}
              </span>
            </div>
            <div className="space-y-1">
              <label className="text-zinc-500 block uppercase text-[9px] font-bold">ScrapeBadger scraper</label>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${config?.scrapebadger_configured ? 'bg-emerald-500/10 text-emerald-400' : 'bg-zinc-800 text-zinc-400'}`}>
                {config?.scrapebadger_configured ? 'API Connected' : 'Not Configured'}
              </span>
            </div>
          </div>
        </div>

        {/* Dynamic Verification / Dependencies */}
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
          <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-blue-400" /> Local System Diagnostics
          </h3>
          {config?.dependencies && (
            <div className="space-y-3 font-mono text-[11px]">
              {Object.entries(config.dependencies).map(([dep, isPresent]) => (
                <div key={dep} className="flex justify-between items-center border-b border-[#1f1f23] pb-1.5">
                  <span className="text-zinc-400 font-bold uppercase">{dep}</span>
                  <span className={`px-2 py-0.5 rounded font-bold text-[9px] ${isPresent ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                    {isPresent ? "AVAILABLE" : "MISSING"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* Provider Health Registry Logs */}
      {config?.provider_health && Object.keys(config.provider_health).length > 0 && (
        <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
          <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" /> Provider Health & Metric Registry
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#1f1f23] text-zinc-500 text-[10px] uppercase font-bold">
                  <th className="pb-3">Category</th>
                  <th className="pb-3">Provider</th>
                  <th className="pb-3 text-right">Success Rate</th>
                  <th className="pb-3 text-right">Avg Latency</th>
                  <th className="pb-3 text-right">Total Requests</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(config.provider_health).map(([category, providers]) => 
                  Object.entries(providers).map(([pName, stats]) => (
                    <tr key={`${category}-${pName}`} className="border-b border-[#1f1f23]/40 hover:bg-[#121215]/30">
                      <td className="py-2.5 text-zinc-400 capitalize">{category}</td>
                      <td className="py-2.5 text-white font-bold">{pName}</td>
                      <td className="py-2.5 text-right font-bold text-emerald-400">
                        {Math.round(stats.success_rate * 100)}%
                      </td>
                      <td className="py-2.5 text-right text-zinc-400">
                        {stats.average_latency > 0 ? `${stats.average_latency.toFixed(3)}s` : "N/A"}
                      </td>
                      <td className="py-2.5 text-right text-zinc-500">{stats.total_requests}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  );
}
