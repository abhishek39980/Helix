import React from 'react';
import { FileVideo, Fingerprint, Cpu } from 'lucide-react';

export default function MediaForensics({ analysis, backendUrl }) {
  if (!analysis) return null;

  const isVideo = (filename) => {
    if (!filename) return false;
    const lower = filename.toLowerCase();
    return ['.mp4', '.mov', '.webm', '.avi', '.mkv'].some(ext => lower.endsWith(ext));
  };

  const isImage = (filename) => {
    if (!filename) return false;
    const lower = filename.toLowerCase();
    return ['.jpg', '.jpeg', '.png', '.webp', '.gif'].some(ext => lower.endsWith(ext));
  };

  const mediaSource = analysis.saved_path ? `${backendUrl}${analysis.saved_path}` : null;

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left: Media container & details */}
        <div className="lg:col-span-7 space-y-6">
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
              <FileVideo className="w-4 h-4 text-blue-400" /> Source Media Container Viewport
            </h3>
            
            <div className="aspect-video bg-[#070708] border border-[#1f1f23] rounded-lg overflow-hidden flex items-center justify-center relative group">
              <div className="absolute inset-0 bg-radial-gradient(circle, transparent 70%, #000 100%)"></div>
              
              {mediaSource ? (
                isVideo(analysis.filename) ? (
                  <video 
                    src={mediaSource} 
                    controls 
                    className="w-full h-full object-contain z-10"
                  />
                ) : isImage(analysis.filename) ? (
                  <img 
                    src={mediaSource} 
                    alt={analysis.filename} 
                    className="w-full h-full object-contain z-10"
                  />
                ) : (
                  <div className="text-center p-6 space-y-4 z-10">
                    <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 mx-auto flex items-center justify-center animate-pulse">
                      <FileVideo className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-xs font-mono text-zinc-300 font-bold">{analysis.filename}</p>
                      <p className="text-[10px] font-mono text-zinc-600 mt-1">Resolution: {analysis.dimensions} | Format Unsupported for Preview</p>
                    </div>
                  </div>
                )
              ) : (
                <div className="text-center p-6 space-y-4 z-10">
                  <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 mx-auto flex items-center justify-center animate-pulse">
                    <FileVideo className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs font-mono text-zinc-300 font-bold">{analysis.filename}</p>
                    <p className="text-[10px] font-mono text-zinc-600 mt-1">Resolution: {analysis.dimensions} | Stream Container: Active (Simulated Preview)</p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Hash Card */}
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-blue-400" /> Structural Hash Fingerprint
            </h3>
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                <span className="text-zinc-500 uppercase text-[10px]">Perceptual Hash (pHash)</span>
                <span className="text-white font-bold tracking-wider">{analysis.phash}</span>
              </div>
              <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                <span className="text-zinc-500 uppercase text-[10px]">MD5 Signature</span>
                <span className="text-white font-bold">{analysis.md5 || 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: EXIF Metadata */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" /> Embedded Hardware EXIF Records
            </h3>

            {analysis.exif && (
              <div className="space-y-3 font-mono text-xs">
                <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                  <span className="text-zinc-500">EXIF Tags Extracted</span>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase font-mono ${analysis.exif.found ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : 'text-amber-400 bg-amber-500/10 border-amber-500/20'}`}>
                    {analysis.exif.found ? "TAGS DETECTED" : "STRIPPED / PURGED"}
                  </span>
                </div>
                <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                  <span className="text-zinc-500">Hardware Model</span>
                  <span className="text-white font-bold">{analysis.exif.camera_model || "Sanitized"}</span>
                </div>
                <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                  <span className="text-zinc-500">GPS Coordinates (lat, lon)</span>
                  <span className="text-zinc-400">{analysis.exif.latitude ? `${analysis.exif.latitude}, ${analysis.exif.longitude}` : "No GPS Metadata Found"}</span>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
