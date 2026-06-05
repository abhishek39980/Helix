import React from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

export default function RadarSignals({ signalBreakdown }) {
  if (!signalBreakdown) return null;

  const data = Object.entries(signalBreakdown).map(([layer, score]) => ({
    subject: layer.toUpperCase(),
    score: score,
    fullMark: 50,
  }));

  return (
    <div className="w-full h-60 bg-[#070708] border border-[#1f1f23] rounded-lg p-2 flex items-center justify-center">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
          <PolarGrid stroke="#1f1f23" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748B', fontSize: 8, fontFamily: 'monospace' }} />
          <PolarRadiusAxis angle={30} domain={[0, 50]} tick={{ fill: '#475569', fontSize: 8 }} />
          <Radar 
            name="Signals" 
            dataKey="score" 
            stroke="#3b82f6" 
            fill="#3b82f6" 
            fillOpacity={0.2} 
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
