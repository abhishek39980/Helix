import React from 'react';
import { ShieldAlert, Search, RefreshCw } from 'lucide-react';

export default function Header({ searchQuery, setSearchQuery, onResetDemo, analysis }) {
  return (
    <header className="h-14 border-b border-[#1f1f23] bg-[#0c0c0e] px-6 flex items-center justify-between z-10 shrink-0 font-mono">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-blue-900/30 border border-blue-500/30 flex items-center justify-center">
          <ShieldAlert className="w-4 h-4 text-blue-400" />
        </div>
        <div>
          <h1 className="text-xs font-bold tracking-[0.2em] text-white uppercase flex items-center gap-2">
            Helix <span className="px-1.5 py-0.5 rounded text-[8px] bg-blue-500/10 border border-blue-500/20 text-blue-400 tracking-normal font-normal">FORENSIC CORE v2.4</span>
          </h1>
          <p className="text-[9px] text-zinc-500 tracking-tighter">SECURE OSINT GATEWAY</p>
        </div>
      </div>

      <div className="flex items-center gap-6">
        <div className="relative w-64 hidden md:block">
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search suspect handle, hash, url..." 
            className="w-full bg-[#121215] border border-[#1f1f23] rounded px-3 py-1.5 pl-8 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-blue-500/50 transition-colors"
          />
          <Search className="w-3.5 h-3.5 text-zinc-600 absolute left-2.5 top-2.5" />
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#121215] border border-[#1f1f23]">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-[10px] text-zinc-500 uppercase">SYS: ACTIVE</span>
          </div>
          
          <button 
            onClick={onResetDemo} 
            className="p-1.5 rounded hover:bg-[#121215] border border-transparent hover:border-[#1f1f23] text-zinc-500 hover:text-zinc-200 transition-all flex items-center gap-1"
            title="Reload Demo Data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
