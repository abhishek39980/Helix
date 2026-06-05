import React, { useEffect } from 'react';
import { X, CheckCircle, AlertTriangle, AlertCircle, Info } from 'lucide-react';

export default function Toast({ message, type = 'info', onClose, duration = 4000 }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const styles = {
    success: 'bg-[#0f2d1e] border-emerald-500/30 text-emerald-400',
    error: 'bg-[#2d0f0f] border-red-500/30 text-red-400',
    warning: 'bg-[#2d220f] border-amber-500/30 text-amber-400',
    info: 'bg-[#0f1f2d] border-blue-500/30 text-blue-400',
  };

  const icons = {
    success: <CheckCircle className="w-4 h-4 text-emerald-400" />,
    error: <AlertCircle className="w-4 h-4 text-red-400" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400" />,
    info: <Info className="w-4 h-4 text-blue-400" />,
  };

  return (
    <div className={`flex items-center justify-between gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-md animate-in slide-in-from-bottom-2 duration-300 ${styles[type] || styles.info}`}>
      <div className="flex items-center gap-2 text-xs font-mono">
        {icons[type]}
        <span>{message}</span>
      </div>
      <button onClick={onClose} className="p-0.5 hover:bg-white/10 rounded transition-colors">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
