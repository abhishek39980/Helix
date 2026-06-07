import sys

with open("frontend/src/components/tabs/MediaForensics.jsx", "r", encoding="utf-8") as f:
    content = f.read()

# Update imports
old_imports = """import React from 'react';
import { FileVideo, Fingerprint, Cpu } from 'lucide-react';"""

new_imports = """import React from 'react';
import { FileVideo, Fingerprint, Cpu, Film, Activity, Layers, AlertTriangle } from 'lucide-react';"""

content = content.replace(old_imports, new_imports)

# Replace Hash Card block
old_hash_card = """          {/* Hash Card */}
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
          </div>"""

new_hash_card = """          {/* Hash Card */}
          <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
            <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-blue-400" /> Structural {analysis.video_analysis ? "Video" : "Hash"} Fingerprint
            </h3>
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                <span className="text-zinc-500 uppercase text-[10px]">{analysis.video_analysis ? "Aggregate Video pHash" : "Perceptual Hash (pHash)"}</span>
                <span className="text-white font-bold tracking-wider">{analysis.phash}</span>
              </div>
              <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                <span className="text-zinc-500 uppercase text-[10px]">MD5 Signature</span>
                <span className="text-white font-bold">{analysis.md5 || 'N/A'}</span>
              </div>
              
              {analysis.video_analysis && (
                <>
                  <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                    <span className="text-zinc-500 uppercase text-[10px]">Sampled Frames</span>
                    <span className="text-white font-bold">{analysis.video_analysis.frames_sampled} frames</span>
                  </div>
                  <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                    <span className="text-zinc-500 uppercase text-[10px]">Video Duration</span>
                    <span className="text-white font-bold">{analysis.video_analysis.duration} s</span>
                  </div>
                  <div className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center">
                    <span className="text-zinc-500 uppercase text-[10px]">Framerate (FPS)</span>
                    <span className="text-white font-bold">{analysis.video_analysis.fps}</span>
                  </div>
                </>
              )}
            </div>
          </div>"""

content = content.replace(old_hash_card, new_hash_card)

# Insert Scene Changes and Frame Fingerprints
video_forensics_sections = """        {/* Video Extended Forensics */}
        {analysis.video_analysis && (
          <>
            <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
                <Activity className="w-4 h-4 text-rose-400" /> Scene Change Detection
              </h3>
              {analysis.video_analysis.scene_changes?.length > 0 ? (
                <div className="space-y-3 font-mono text-xs">
                  {analysis.video_analysis.scene_changes.map((scene, idx) => (
                    <div key={idx} className="p-3 bg-[#121215] border border-[#1f1f23] rounded-lg flex justify-between items-center relative overflow-hidden group">
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-rose-500 to-rose-900 opacity-50 group-hover:opacity-100 transition-opacity"></div>
                      <div className="flex items-center gap-3 ml-2">
                        <AlertTriangle className="w-3 h-3 text-rose-500" />
                        <span className="text-zinc-300">Timestamp: {scene.timestamp}s</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="flex flex-col text-right">
                          <span className="text-[9px] text-zinc-500 uppercase">Hamming Dist</span>
                          <span className="text-white font-bold">{scene.distance}</span>
                        </div>
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase ${scene.distance > 20 ? 'text-rose-400 bg-rose-500/10 border-rose-500/20' : 'text-amber-400 bg-amber-500/10 border-amber-500/20'}`}>
                          {scene.distance > 20 ? 'HARD CUT' : 'TRANSITION'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="p-4 text-center border border-dashed border-[#1f1f23] rounded-lg text-zinc-500 text-xs font-mono">
                  No significant scene changes detected
                </div>
              )}
            </div>

            <div className="bg-[#0c0c0e] border border-[#1f1f23] rounded-xl p-6 space-y-4">
              <h3 className="text-xs font-bold text-white tracking-widest uppercase border-b border-[#1f1f23] pb-3 flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" /> Frame Fingerprints
              </h3>
              <div className="font-mono text-xs max-h-64 overflow-y-auto pr-2 custom-scrollbar space-y-2">
                {analysis.frame_hashes?.map((hash, idx) => (
                  <div key={idx} className="p-2.5 bg-[#121215] border border-[#1f1f23] rounded-md flex justify-between items-center hover:border-indigo-500/30 transition-colors">
                    <span className="text-zinc-500">Frame {idx + 1}</span>
                    <span className="text-indigo-200 tracking-wider">{hash}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        </div>

        {/* Right: EXIF Metadata */}"""

content = content.replace('        </div>\n\n        {/* Right: EXIF Metadata */}', video_forensics_sections)

with open("frontend/src/components/tabs/MediaForensics.jsx", "w", encoding="utf-8") as f:
    f.write(content)

print("UI Patch successfully applied!")
