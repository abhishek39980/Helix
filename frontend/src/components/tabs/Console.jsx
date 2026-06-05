import React from 'react';
import { Terminal } from 'lucide-react';

export default function Console({ terminalLogs }) {
  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <section className="bg-black border border-zinc-900 rounded-xl overflow-hidden shadow-2xl">
        <div className="bg-[#0c0c0e] px-4 py-2 border-b border-zinc-900 flex items-center justify-between font-mono">
          <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-blue-500" /> Core System Console Out
          </span>
          <div className="flex gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/20 border border-red-500/40"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/20 border border-yellow-500/40"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/20 border border-green-500/40"></span>
          </div>
        </div>
        <div className="p-6 h-96 overflow-y-auto space-y-1.5 font-mono text-xs bg-[#050506]">
          {terminalLogs.map((log, index) => (
            <div key={index} className="flex gap-3">
              <span className="text-zinc-700 select-none">root@helix:~$</span>
              <span className={
                log.includes('SUCCESS') || log.includes('DATA:') ? 'text-emerald-400' : 
                log.includes('WARN') ? 'text-amber-400 animate-pulse' : 
                log.includes('ERROR') ? 'text-red-400' : 
                'text-zinc-400'
              }>{log}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
