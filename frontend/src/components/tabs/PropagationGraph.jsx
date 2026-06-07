import React, { useState } from 'react';
import { Network, HelpCircle, Layers } from 'lucide-react';

export default function PropagationGraph({ graph }) {
  const [hoveredNode, setHoveredNode] = useState(null);

  if (!graph || !graph.nodes || graph.nodes.length === 0) {
    return (
      <div className="p-8 text-center border border-dashed border-[#1f1f23] rounded-xl text-zinc-500 text-xs font-mono">
        No distribution graph mapped for this trace session.
      </div>
    );
  }

  const getNodeColor = (data) => {
    const p = data.platform?.toLowerCase() || '';
    if (p.includes('helix')) return '#3b82f6'; // blue
    if (p.includes('telegram')) return '#0ea5e9'; // sky
    if (p.includes('twitter') || p.includes('x')) return '#27272a'; // zinc-800
    if (p.includes('reddit')) return '#f97316'; // orange
    if (p.includes('tiktok')) return '#f43f5e'; // rose
    return '#6b7280'; // grey
  };

  return (
    <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4 relative overflow-hidden">
      
      {/* Header / Actions bar */}
      <div className="flex justify-between items-center border-b border-[#1f1f23] pb-3">
        <h3 className="text-xs font-bold text-white tracking-widest uppercase flex items-center gap-2">
          <Network className="w-4 h-4 text-blue-400" /> Dissemination Vector Graph
        </h3>
        <div className="flex items-center gap-1.5 text-[9px] font-mono text-zinc-500">
          <Layers className="w-3.5 h-3.5" />
          <span>Interactive SVG Canvas (Active)</span>
        </div>
      </div>

      {/* SVG Container Viewport */}
      <div className="relative h-96 bg-[#070708] border border-[#1f1f23] rounded-lg overflow-hidden flex items-center justify-center">
        
        {/* Legend */}
        <div className="absolute top-4 left-4 z-10 p-2.5 rounded bg-[#0c0c0e]/95 border border-[#1f1f23] space-y-1.5 text-[9px] font-mono">
          <span className="text-zinc-500 uppercase block font-bold">Node Legend</span>
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span><span className="text-zinc-300">HELIX Session</span></div>
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-sky-500"></span><span className="text-zinc-300">Telegram Post</span></div>
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-zinc-700"></span><span className="text-zinc-300">X (Twitter) Post</span></div>
          <div className="flex items-center gap-2"><span className="w-2.5 h-2.5 rounded-full bg-orange-500"></span><span className="text-zinc-300">Reddit Post</span></div>
        </div>

        {/* SVG Drawing Area */}
        <svg className="absolute inset-0 w-full h-full">
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="18"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#1f1f23" />
            </marker>
          </defs>

          {/* Render Connections / Edges */}
          {graph.edges?.map((edge, idx) => {
            const src = graph.nodes.find(n => n.id === edge.source);
            const tgt = graph.nodes.find(n => n.id === edge.target);
            if (!src || !tgt) return null;
            
            return (
              <g key={idx}>
                <line 
                  x1={src.position.x} 
                  y1={src.position.y} 
                  x2={tgt.position.x} 
                  y2={tgt.position.y} 
                  stroke="#1f1f23" 
                  strokeWidth="2"
                  markerEnd="url(#arrow)"
                />
                <text 
                  x={(src.position.x + tgt.position.x) / 2} 
                  y={(src.position.y + tgt.position.y) / 2 - 5} 
                  fill="#444" 
                  textAnchor="middle"
                  className="text-[7px] font-mono uppercase font-bold"
                >
                  {edge.label || 'Copy'}
                </text>
              </g>
            );
          })}

          {/* Render Nodes */}
          {graph.nodes?.map((node) => {
            const isHovered = hoveredNode === node.id;
            return (
              <g 
                key={node.id} 
                className="cursor-pointer"
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
              >
                <circle 
                  cx={node.position.x} 
                  cy={node.position.y} 
                  r={isHovered ? "14" : "10"} 
                  fill={getNodeColor(node.data)}
                  stroke={isHovered ? "#fff" : "transparent"}
                  strokeWidth="1.5"
                  className="transition-all duration-200"
                />
                <text 
                  x={node.position.x} 
                  y={node.position.y + 24} 
                  fill={isHovered ? "#fff" : "#888"} 
                  textAnchor="middle" 
                  className="text-[8px] font-mono uppercase font-bold"
                >
                  {node.data.username || node.data.label}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover card */}
        {hoveredNode && (
          <div className="absolute bottom-4 right-4 p-3.5 bg-[#0c0c0e]/95 border border-blue-500/30 rounded-xl space-y-1 w-56 text-[10px] font-mono shadow-xl animate-in fade-in duration-200">
            <span className="text-zinc-600 block uppercase text-[8px] tracking-widest font-bold">Node Metadata</span>
            <span className="text-white font-bold block">{graph.nodes.find(n => n.id === hoveredNode)?.data.platform}</span>
            <span className="text-zinc-400 block mt-1">Handle: {graph.nodes.find(n => n.id === hoveredNode)?.data.username}</span>
            <span className="text-zinc-500 block">Mutation: {graph.nodes.find(n => n.id === hoveredNode)?.data.mutation}</span>
            <span className="text-zinc-500 block">Similarity: {graph.nodes.find(n => n.id === hoveredNode)?.data.similarity}%</span>
          </div>
        )}
      </div>

    </div>
  );
}
