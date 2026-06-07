import React from 'react';
import { Clock, MessageSquare, Repeat, Share2, AlertOctagon } from 'lucide-react';

export default function TimelineView({ timeline }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-8 text-center border border-dashed border-[#1f1f23] rounded-xl text-zinc-500 text-xs font-mono">
        No chronologies mapped for this trace session.
      </div>
    );
  }

  const getEventIcon = (platform) => {
    switch (platform?.toLowerCase()) {
      case 'telegram':
        return <MessageSquare className="w-3.5 h-3.5 text-sky-400" />;
      case 'x (twitter)':
      case 'twitter':
        return <Repeat className="w-3.5 h-3.5 text-white" />;
      case 'reddit':
        return <Share2 className="w-3.5 h-3.5 text-orange-400" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-zinc-400" />;
    }
  };

  return (
    <div className="relative border-l border-[#1f1f23] ml-4 pl-6 space-y-6 py-2">
      {timeline.map((event, idx) => (
        <div key={idx} className="relative group">
          
          {/* Vertical marker circle */}
          <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full bg-[#070708] border-2 border-[#1f1f23] flex items-center justify-center group-hover:border-zinc-500 transition-colors">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
          </div>

          {/* Card */}
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-4 space-y-2 hover:border-zinc-800 transition-colors">
            
            {/* Header info */}
            <div className="flex justify-between items-center text-[10px] font-mono">
              <span className="text-zinc-500 flex items-center gap-1.5">
                <Clock className="w-3 h-3 text-zinc-600" />
                {event.date}
              </span>
              <span className="text-blue-400 font-bold uppercase tracking-wider">
                Event {idx + 1}
              </span>
            </div>

            {/* Content body */}
            <div className="flex items-start gap-3 mt-1">
              <div className="p-1.5 rounded-lg bg-[#121215] border border-[#1f1f23] mt-0.5">
                {getEventIcon(event.platform)}
              </div>
              <div className="space-y-1">
                <p className="text-xs font-bold text-white font-mono flex items-center gap-1.5">
                  {event.platform} Account: <span className="text-zinc-400 font-normal">{event.username}</span>
                </p>
                <p className="text-xs text-zinc-400 font-sans leading-relaxed">
                  {event.event}
                </p>
              </div>
            </div>

            {/* Source link */}
            {event.url && (
              <div className="pt-2 border-t border-[#121215] text-[9px] font-mono">
                <a 
                  href={event.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-zinc-500 hover:text-blue-400 transition-colors truncate block"
                >
                  Source Link: {event.url}
                </a>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
