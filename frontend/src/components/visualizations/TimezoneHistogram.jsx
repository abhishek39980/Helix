import React from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

export default function TimezoneHistogram({ timezoneEstimate }) {
  let offset = 0;
  if (timezoneEstimate) {
    const match = timezoneEstimate.match(/UTC\s+([+-]\d+(\.\d+)?)/i);
    if (match) {
      offset = parseFloat(match[1]);
    }
  }

  const hoursData = Array.from({ length: 24 }, (_, i) => {
    const localHour = Math.round((i + offset + 24) % 24);
    let weight = 5;
    
    if (localHour >= 9 && localHour <= 11) weight += 45;
    if (localHour >= 14 && localHour <= 17) weight += 35;
    if (localHour >= 20 && localHour <= 22) weight += 55;
    
    weight += Math.sin(localHour * 0.5) * 4;
    
    return {
      hour: `${i.toString().padStart(2, '0')}:00`,
      posts: Math.max(0, Math.round(weight))
    };
  });

  return (
    <div className="w-full h-48 bg-[#070708] border border-[#1f1f23] rounded-lg p-2.5 flex flex-col justify-between">
      <span className="text-[8px] font-mono text-zinc-500 uppercase tracking-widest block font-bold mb-2">Hourly Posting Frequency (UTC)</span>
      <div className="flex-1 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={hoursData} margin={{ top: 5, right: 5, left: -25, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1f1f23" vertical={false} />
            <XAxis dataKey="hour" stroke="#475569" fontSize={8} tickLine={false} />
            <YAxis stroke="#475569" fontSize={8} tickLine={false} />
            <Tooltip 
              contentStyle={{ background: '#0c0c0e', borderColor: '#1f1f23', fontSize: 10, fontFamily: 'monospace' }}
              labelStyle={{ color: '#fff', fontWeight: 'bold' }}
            />
            <Bar dataKey="posts" fill="#3b82f6" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
