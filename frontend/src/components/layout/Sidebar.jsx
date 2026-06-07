import React from 'react';
import { 
  BarChart3, Fingerprint, FileVideo, Clock, GitFork, 
  Terminal, Settings, Shield, Network 
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab }) {
  const primaryNavItems = [
    { id: 'dashboard', label: 'OVERVIEW', icon: BarChart3 },
    { id: 'profile', label: 'PROFILE INTEL', icon: Fingerprint },
    { id: 'media', label: 'MEDIA FORENSICS', icon: FileVideo },
    { id: 'timeline', label: 'TIMELINE ANALYSER', icon: Clock },
    { id: 'network', label: 'PROPAGATION NET', icon: GitFork },
    { id: 'trace', label: 'GLOBAL TRACE', icon: Network },
  ];

  const systemNavItems = [
    { id: 'console', label: 'SECURE CONSOLE', icon: Terminal },
    { id: 'settings', label: 'SCAN SETTINGS', icon: Settings },
  ];

  return (
    <aside className="w-56 border-r border-[#1f1f23] bg-[#0c0c0e] flex flex-col justify-between shrink-0 font-mono">
      <div className="py-4">
        <div className="px-4 mb-4 text-[9px] font-bold text-zinc-600 tracking-wider uppercase">OSINT Operations</div>
        <nav className="space-y-0.5 px-2">
          {primaryNavItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded text-left transition-all ${
                activeTab === item.id 
                  ? 'bg-blue-900/20 text-white font-bold border border-blue-500/20 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]' 
                  : 'text-zinc-500 hover:text-zinc-300 border border-transparent hover:bg-zinc-900/30'
              }`}
            >
              <item.icon className={`w-4 h-4 ${activeTab === item.id ? 'text-blue-400' : 'text-zinc-600'}`} />
              <span className="text-[10px] tracking-wider uppercase">{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="border-t border-[#1f1f23] my-4 pt-4">
          <div className="px-4 mb-2 text-[9px] font-bold text-zinc-600 tracking-wider uppercase">System Tools</div>
          <nav className="space-y-0.5 px-2">
            {systemNavItems.map(item => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded text-left transition-all ${
                  activeTab === item.id 
                    ? 'bg-zinc-800/40 text-white font-bold border border-[#1f1f23]' 
                    : 'text-zinc-500 hover:text-zinc-300 border border-transparent hover:bg-zinc-900/30'
                }`}
              >
                <item.icon className="w-4 h-4 text-zinc-600" />
                <span className="text-[10px] tracking-wider uppercase">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="p-4 border-t border-[#1f1f23] bg-[#09090b] flex items-center gap-3">
        <div className="w-7 h-7 rounded-full bg-blue-950 border border-blue-500/30 flex items-center justify-center">
          <Shield className="w-3.5 h-3.5 text-blue-400" />
        </div>
        <div>
          <div className="text-[10px] font-bold text-zinc-300">ANALYST_01</div>
          <div className="text-[8px] text-zinc-600 uppercase tracking-tighter">ROLE: LEI_AGENT</div>
        </div>
      </div>
    </aside>
  );
}
