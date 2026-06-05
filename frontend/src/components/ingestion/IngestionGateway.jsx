import React, { useState } from 'react';
import { Database, Upload, Link } from 'lucide-react';

export default function IngestionGateway({ 
  ingestMode, 
  setIngestMode, 
  mediaUrl, 
  setMediaUrl, 
  onFileUpload, 
  onLinkSubmit, 
  loading,
  uploadProgress
}) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      onFileUpload({ target: { files } });
    }
  };

  return (
    <div className="max-w-xl mx-auto my-12 bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-8 shadow-xl text-center space-y-6">
      <div className="w-12 h-12 rounded-full bg-blue-500/10 border border-blue-500/20 mx-auto flex items-center justify-center">
        <Database className="w-6 h-6 text-blue-400" />
      </div>
      <div className="space-y-2">
        <h3 className="text-sm font-semibold text-white tracking-wider uppercase">Forensic Intake Ingestion</h3>
        <p className="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
          Select target ingest channel. Upload a suspicious media container or submit a social profile URL path to start tracking.
        </p>
      </div>

      <div className="flex gap-2 p-1 bg-[#121215] border border-[#1f1f23] rounded-lg">
        <button 
          onClick={() => setIngestMode('upload')}
          className={`flex-1 text-[10px] font-mono py-2 rounded-md font-bold transition-all ${ingestMode === 'upload' ? 'bg-blue-600 text-white shadow' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          BINARY FILE UPLOAD
        </button>
        <button 
          onClick={() => setIngestMode('link')}
          className={`flex-1 text-[10px] font-mono py-2 rounded-md font-bold transition-all ${ingestMode === 'link' ? 'bg-blue-600 text-white shadow' : 'text-zinc-500 hover:text-zinc-300'}`}
        >
          SOCIAL CHANNEL SCAN
        </button>
      </div>

      {ingestMode === 'upload' ? (
        <div 
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border border-dashed rounded-xl p-12 text-center cursor-pointer transition-all relative group bg-[#09090b] ${
            dragOver ? 'border-blue-500 bg-blue-500/5 shadow-md shadow-blue-500/5' : 'border-zinc-800 hover:border-blue-500/50'
          }`}
        >
          <input 
            type="file" 
            className="absolute inset-0 opacity-0 cursor-pointer" 
            onChange={onFileUpload} 
            disabled={loading}
          />
          <Upload className="w-8 h-8 text-zinc-600 mx-auto mb-4 group-hover:text-blue-400 transition-colors" />
          <span className="text-xs text-zinc-400 font-bold block mb-1">Drag and drop file here</span>
          <span className="text-[10px] text-zinc-600 block mb-2">Supports MP4, PNG, JPG up to 100MB</span>
          
          {loading && (
            <div className="w-full mt-4 space-y-2">
              <div className="flex justify-between text-[10px] font-mono text-zinc-400">
                <span>Ingesting binary stream...</span>
                <span>{uploadProgress || 0}%</span>
              </div>
              <div className="h-1.5 w-full bg-[#121215] border border-[#1f1f23] rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full transition-all duration-300" style={{ width: `${uploadProgress || 0}%` }}></div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="relative">
            <input 
              type="text" 
              value={mediaUrl}
              onChange={(e) => setMediaUrl(e.target.value)}
              placeholder="https://x.com/username..." 
              className="w-full bg-[#121215] border border-[#1f1f23] rounded-lg px-4 py-3 pl-10 text-xs text-zinc-200 focus:outline-none focus:border-blue-500"
            />
            <Link className="w-4 h-4 text-zinc-600 absolute left-3 top-3.5" />
          </div>
          <button 
            onClick={onLinkSubmit}
            disabled={loading || !mediaUrl}
            className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-3 rounded-lg text-xs tracking-widest transition-all disabled:opacity-30 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                EXECUTING THREAT ANALYSIS...
              </>
            ) : (
              "COMMENCE PIPELINE SWEEP"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
