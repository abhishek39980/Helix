import React from 'react';
import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings({ backendUrl }) {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-6">
        <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
          <SettingsIcon className="w-4 h-4 text-blue-400" /> Pipeline Configuration Settings
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
          <div className="space-y-2">
            <label className="text-zinc-500 block uppercase text-[9px] font-bold">API Ingress Target Host</label>
            <input type="text" readOnly value={backendUrl} className="w-full bg-[#121215] border border-[#1f1f23] rounded p-2 text-zinc-300" />
          </div>
          <div className="space-y-2">
            <label className="text-zinc-500 block uppercase text-[9px] font-bold">Vision Geocoding Endpoint</label>
            <input type="text" readOnly value="LM Studio API (env: LM_STUDIO_URL)" className="w-full bg-[#121215] border border-[#1f1f23] rounded p-2 text-zinc-300" />
          </div>
          <div className="space-y-2">
            <label className="text-zinc-500 block uppercase text-[9px] font-bold">Geocoding Provider API Key</label>
            <input type="password" readOnly value="••••••••••••••••••••" className="w-full bg-[#121215] border border-[#1f1f23] rounded p-2 text-zinc-600" />
          </div>
          <div className="space-y-2">
            <label className="text-zinc-500 block uppercase text-[9px] font-bold">Scraping Provider Endpoint</label>
            <input type="text" readOnly value="ScrapeBadger v1 (env: SCRAPEBADGER_API_KEY)" className="w-full bg-[#121215] border border-[#1f1f23] rounded p-2 text-zinc-300" />
          </div>
        </div>
      </div>
    </div>
  );
}
