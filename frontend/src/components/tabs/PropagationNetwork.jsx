import React from 'react';
import { Network, Filter, Share2 } from 'lucide-react';

export default function PropagationNetwork({ 
  analysis, 
  hoveredNode, 
  setHoveredNode 
}) {
  if (!analysis) return null;

  // Network graph derived from live mutation tree variants
  const networkNodes = (analysis.mutation_tree?.variants || []).map((v, idx) => ({
    id: v.id,
    label: v.account,
    type: v.id === 'current_uploaded' ? 'media' : v.id === 'node_root' ? 'user' : 'platform',
    x: 80 + (idx % 3) * 170,
    y: 120 + Math.floor(idx / 3) * 130,
    details: `${v.platform} — ${v.mutation}`
  }));

  const networkEdges = (analysis.mutation_tree?.variants || []).reduce((edges, v, idx, arr) => {
    if (idx > 0) edges.push({ source: arr[idx - 1].id, target: v.id, type: 'Propagation' });
    return edges;
  }, []);

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
        <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
          <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2">
            <Network className="w-4 h-4 text-blue-400" /> Distribution Node Propagation Graph
          </h3>
          <div className="flex items-center gap-2">
            <button className="px-2 py-1 rounded bg-[#121215] border border-[#1f1f23] text-[9px] font-mono text-zinc-400 uppercase flex items-center gap-1"><Filter className="w-3 h-3" /> Filters</button>
            <button className="p-1 rounded bg-[#121215] border border-[#1f1f23] text-[#555]"><Share2 className="w-3.5 h-3.5" /></button>
          </div>
        </div>

        {/* Network Canvas simulation */}
        <div className="relative h-96 bg-[#070708] border border-[#1f1f23] rounded-lg overflow-hidden flex items-center justify-center">
          <div className="absolute top-4 left-4 z-10 p-2.5 rounded bg-[#0c0c0e]/95 border border-[#1f1f23] space-y-1.5 text-[9px] font-mono">
            <span className="text-zinc-500 uppercase block font-bold">Graph Legend</span>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500"></span><span className="text-zinc-300">Suspect Origin</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-emerald-500"></span><span className="text-zinc-300">Replication User</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-cyan-400"></span><span className="text-zinc-300">Media Asset</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-zinc-600"></span><span className="text-zinc-300">Web Platforms</span></div>
          </div>

          <svg className="absolute inset-0 w-full h-full">
            {/* Edges */}
            {networkEdges.map((edge, idx) => {
              const src = networkNodes.find(n => n.id === edge.source);
              const tgt = networkNodes.find(n => n.id === edge.target);
              if (!src || !tgt) return null;
              return (
                <g key={idx}>
                  <line 
                    x1={src.x} 
                    y1={src.y} 
                    x2={tgt.x} 
                    y2={tgt.y} 
                    stroke="#1f1f23" 
                    strokeWidth="1.5"
                    strokeDasharray={edge.type === 'Amplification' ? '4 4' : '0'}
                  />
                  <text 
                    x={(src.x + tgt.x) / 2} 
                    y={(src.y + tgt.y) / 2 - 5} 
                    fill="#444" 
                    textAnchor="middle"
                    className="text-[7px] font-mono uppercase"
                  >
                    {edge.type}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {networkNodes.map((node) => {
              const isHovered = hoveredNode === node.id;
              return (
                <g 
                  key={node.id} 
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                >
                  <circle 
                    cx={node.x} 
                    cy={node.y} 
                    r={isHovered ? "14" : "10"} 
                    fill={
                      node.id === 'node_root' ? '#2563eb' :
                      node.type === 'media' ? '#06b6d4' :
                      node.type === 'platform' ? '#27272a' :
                      node.type === 'bot' ? '#dc2626' :
                      '#10b981'
                    }
                    stroke={isHovered ? "#fff" : "transparent"}
                    strokeWidth="1.5"
                    className="transition-all duration-200"
                  />
                  <text 
                    x={node.x} 
                    y={node.y + 24} 
                    fill={isHovered ? "#fff" : "#888"} 
                    textAnchor="middle" 
                    className="text-[8px] font-mono uppercase font-bold"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Interactive floating card on hover */}
          {hoveredNode && (
            <div className="absolute bottom-4 right-4 p-3.5 bg-[#0c0c0e]/95 border border-blue-500/30 rounded-xl space-y-1 w-56 text-[10px] font-mono shadow-xl animate-in fade-in duration-200">
              <span className="text-zinc-600 block uppercase text-[8px] tracking-widest font-bold">Node Metadata</span>
              <span className="text-white font-bold block">{networkNodes.find(n => n.id === hoveredNode)?.label}</span>
              <span className="text-zinc-400 block mt-1">{networkNodes.find(n => n.id === hoveredNode)?.details}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
