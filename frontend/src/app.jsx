import React, { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import Sidebar from './components/layout/Sidebar';
import EvidencePanel from './components/layout/EvidencePanel';
import IngestionGateway from './components/ingestion/IngestionGateway';
import Dashboard from './components/tabs/Dashboard';
import ProfileIntel from './components/tabs/ProfileIntel';
import MediaForensics from './components/tabs/MediaForensics';
import TimelineAnalyser from './components/tabs/TimelineAnalyser';
import PropagationNetwork from './components/tabs/PropagationNetwork';
import Console from './components/tabs/Console';
import Settings from './components/tabs/Settings';
import DisseminationTracker from './components/tabs/DisseminationTracker';
import Toast from './components/ui/Toast';
import { Compass } from 'lucide-react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [ingestMode, setIngestMode] = useState('upload');
  const [mediaUrl, setMediaUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [captionInput, setCaptionInput] = useState("");
  const [textAnalysis, setTextAnalysis] = useState(null);
  const [textLoading, setTextLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedTimelineEvent, setSelectedTimelineEvent] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [toasts, setToasts] = useState([]);
  
  const [terminalLogs, setTerminalLogs] = useState([
    "CORE: Kernel initialized v2.4.0-stable",
    `NET: Handshake with backend (${BACKEND_URL}) [PENDING]`,
    "SYSTEM: Ready for multi-vector ingestion...",
    "SECURE: Sandbox containment activated."
  ]);

  const addLog = (msg) => {
    setTerminalLogs(prev => [...prev.slice(-12), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const showToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
  };

  const removeToast = (id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  };

  useEffect(() => {
    const saved = localStorage.getItem('helix_session');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setAnalysis(parsed);
        addLog("SYSTEM: Restored active forensic session from local cache.");
      } catch (e) {
        localStorage.removeItem('helix_session');
      }
    }
  }, []);

  const handleFileUpload = (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    setLoading(true);
    setUploadProgress(0);
    addLog(`INIT: Buffering binary stream: ${selectedFile.name}`);

    const formData = new FormData();
    formData.append('file', selectedFile);

    const xhr = new XMLHttpRequest();
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percentComplete = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percentComplete);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          setAnalysis(data);
          localStorage.setItem('helix_session', JSON.stringify(data));
          
          addLog(`DATA: Forensic metadata extraction complete. layers=9`);
          if (data.location_intelligence) {
            addLog(`INTEL: Country geolocated: ${data.location_intelligence.country} (conf=${data.location_intelligence.confidence})`);
          }
          showToast("Forensic analysis completed successfully!", "success");
        } catch (err) {
          addLog(`ERROR: Malformed response from server.`);
          showToast("Failed to parse server response.", "error");
        }
      } else {
        addLog(`ERROR: Ingest failed (HTTP ${xhr.status})`);
        showToast(`Server returned error code: ${xhr.status}`, "error");
      }
      setLoading(false);
      setUploadProgress(0);
    };

    xhr.onerror = () => {
      addLog(`ERROR: Network transmission interrupted.`);
      showToast("Network upload error.", "error");
      setLoading(false);
      setUploadProgress(0);
    };

    xhr.open('POST', `${BACKEND_URL}/api/analyze`);
    const apiKey = import.meta.env.VITE_API_KEY || "";
    if (apiKey) {
      xhr.setRequestHeader("X-API-Key", apiKey);
    }
    xhr.send(formData);
  };

  const handleLinkSubmit = async () => {
    if (!mediaUrl) return;
    setLoading(true);
    addLog(`RESOLVE: Crawling remote OSINT target: ${mediaUrl.substring(0, 30)}...`);

    try {
      const apiKey = import.meta.env.VITE_API_KEY || "";
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers["X-API-Key"] = apiKey;

      const response = await fetch(`${BACKEND_URL}/api/analyze-url`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ url: mediaUrl.trim() })
      });
      if (!response.ok) {
        throw new Error(`Ingest failed (HTTP ${response.status})`);
      }
      const data = await response.json();
      setAnalysis(data);
      localStorage.setItem('helix_session', JSON.stringify(data));
      addLog(`SUCCESS: Target resolved. Node metadata enriched.`);
      if (data.location_intelligence) {
        addLog(`INTEL: Script and linguistic sweep concluded: ${data.location_intelligence.country}`);
      }
      showToast("Forensic analysis complete!", "success");
    } catch (error) {
      addLog(`ERROR: Failed to resolve URL — ${error.message}`);
      showToast(error.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleLinguisticAnalyze = async () => {
    if (!captionInput) return;
    setTextLoading(true);
    addLog(`LIP: Submitting narrative payload to text model...`);
    try {
      const apiKey = import.meta.env.VITE_API_KEY || "";
      const headers = { 'Content-Type': 'application/json' };
      if (apiKey) headers["X-API-Key"] = apiKey;

      const response = await fetch(`${BACKEND_URL}/api/analyze-text`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ caption: captionInput })
      });
      const data = await response.json();
      setTextAnalysis(data);
      addLog(`LIP: Linguistic analysis complete. Bot Probability = ${data.bot_probability}`);
      showToast("Linguistic sweep finished.", "success");
    } catch (e) {
      addLog(`ERROR: Linguistic sweep failed — ${e.message}`);
      showToast("Linguistic analysis failed.", "error");
    } finally {
      setTextLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!analysis || !analysis.id) {
      showToast("No active session ID to export.", "warning");
      return;
    }
    addLog(`EXPORT: Compiling ReportLab PDF payload...`);
    try {
      const apiKey = import.meta.env.VITE_API_KEY || "";
      const headers = {};
      if (apiKey) headers["X-API-Key"] = apiKey;
      
      const response = await fetch(`${BACKEND_URL}/api/export/${analysis.id}/pdf`, { headers });
      if (!response.ok) throw new Error("Server failed to compile PDF");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `omni_track_report_${analysis.id.substring(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      addLog("SUCCESS: PDF report downloaded successfully.");
      showToast("PDF report downloaded.", "success");
    } catch (e) {
      addLog(`ERROR: PDF compilation aborted: ${e.message}`);
      showToast("Failed to download PDF report.", "error");
    }
  };

  const handleExportCSV = async () => {
    if (!analysis || !analysis.id) {
      showToast("No active session ID to export.", "warning");
      return;
    }
    addLog(`EXPORT: Generating CSV data stream...`);
    try {
      const apiKey = import.meta.env.VITE_API_KEY || "";
      const headers = {};
      if (apiKey) headers["X-API-Key"] = apiKey;
      
      const response = await fetch(`${BACKEND_URL}/api/export/${analysis.id}/csv`, { headers });
      if (!response.ok) throw new Error("Server failed to generate CSV");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `omni_track_data_${analysis.id.substring(0, 8)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      addLog("SUCCESS: CSV data downloaded successfully.");
      showToast("CSV data downloaded.", "success");
    } catch (e) {
      addLog(`ERROR: CSV generation aborted: ${e.message}`);
      showToast("Failed to download CSV data.", "error");
    }
  };

  const handleTerminateSession = () => {
    setAnalysis(null);
    localStorage.removeItem('helix_session');
    addLog("SYSTEM: Session terminated. Local workspace caches purged.");
    showToast("Session closed.", "info");
  };

  const triggerFallback = (name) => {
    addLog(`WARN: Remote node unreachable. Bootstrapping simulated intelligence workspace...`);
    const mockData = {
      id: "demo_mock_session_id",
      filename: name,
      md5: "858e72c88f11a8c990263be9161a0d3f",
      phash: "f4c2e8e99b0d33e1",
      dimensions: "1280x720",
      exif: { found: false, camera_model: "Metadata Sanitized (OPSEC Override)" },
      vision_location_report: "**Suspected Location**: Japan / Tokyo Metropolitan Core.\n\n**Visual / OCR Indicators**:\n- Kanji character sequences detected: '江戸前寿司' (Edomae Sushi).\n- Transit signaling architecture matches East Japan Rail specs.\n- Density of cherry blossom canopy suggest peak April vegetative cycle.",
      mutation_tree: {
        variants: [
          { id: "node_root", platform: "Telegram (Source)", timestamp: "2026-06-03 12:01 UTC", account: "@kasamacura", mutation: "Original Stream Capture" },
          { id: "node_v1", platform: "X (Twitter CDN)", timestamp: "2026-06-03 12:15 UTC", account: "@sushi_forensics", mutation: "Compressed Re-encode" },
          { id: "current_uploaded", platform: "Live Inspection Node", timestamp: "2026-06-03 14:47 UTC", account: "System Forensic Uplink", mutation: "Inspected Asset" }
        ]
      },
      temporal_analysis: {
        timezone: "UTC +09:00 (Japan Standard Time)",
        velocity: "STEADY SUSTAINED VELOCITY: Gradual organic audience crawl",
        seed_window: "14 Minutes"
      },
      location_intelligence: {
        country: "Japan",
        state: "Tokyo",
        city: "Chiyoda",
        timezone: "UTC +09:00 (Japan Standard Time)",
        confidence: 0.88,
        evidence: [
          "Japanese script detected in bio: '“肩肘張らずに、本物を。” 江戸前寿司の伝統を大切にしながら...'",
          "Linguistic marker: Edomae sushi terminology ('江戸前寿司')",
          "Timezone consensus: Tokyo Standby offsets aligned with post frequency",
          "Website analysis: profile references .jp top-level domain asset",
          "Social graph clustering of 6 interactive connections reveals dominant geographic cluster in Japan (density: 66%).",
          "Identity resolution geocoded consensus: Japan across 2 platforms."
        ],
        signal_breakdown: {
          "snowflake": 15,
          "explicit": 0,
          "nlp": 5,
          "timezone": 14,
          "language": 35,
          "context": 10,
          "website": 10,
          "exif": 0,
          "visual": 20,
          "social_graph": 25,
          "cross_platform": 25
        },
        social_graph: {
          "country": "Japan",
          "tz_label": "UTC +09:00 (Japan Standard Time)",
          "score": 25,
          "evidence": [
            "Geographic clustering of 6 interactive connections indicates high density in Kanto region, Japan",
            "Strongest interaction weight is with @tokyo_explorer (Japan, weight=45)"
          ],
          "connections": [
            { "username": "tokyo_explorer", "location": "Tokyo, Japan", "weight": 45, "inferred_country": "Japan" },
            { "username": "sushi_lover", "location": "Osaka, Japan", "weight": 35, "inferred_country": "Japan" },
            { "username": "nihon_tech", "location": "Kyoto, Japan", "weight": 25, "inferred_country": "Japan" },
            { "username": "osint_jp", "location": "Tokyo, Japan", "weight": 20, "inferred_country": "Japan" },
            { "username": "travel_asia", "location": "Singapore", "weight": 10, "inferred_country": "Singapore" },
            { "username": "global_intel", "location": "London, UK", "weight": 5, "inferred_country": "United Kingdom" }
          ],
          "clusters": {
            "Japan": 4,
            "Singapore": 1,
            "United Kingdom": 1
          }
        },
        cross_platform: {
          "country": "Japan",
          "tz_label": "UTC +09:00 (Japan Standard Time)",
          "score": 25,
          "evidence": [
            "Matched target handle on GitHub: location resolves to 'Tokyo, Japan'",
            "Matched target handle on Telegram (bio matches Twitter description)"
          ],
          "resolved_profiles": [
            { "platform": "GitHub", "username": "sushi_forensics", "url": "https://github.com/sushi_forensics", "location": "Tokyo, Japan", "status": "resolved", "bio": "Forensic enthusiast and software developer. Building digital provenance tools." },
            { "platform": "Telegram", "username": "sushi_forensics", "url": "https://t.me/sushi_forensics", "location": null, "status": "resolved", "bio": "Analyzing digital footprints and sushi recipes. DM for inquiries." },
            { "platform": "Reddit", "username": "sushi_forensics", "url": "https://reddit.com/user/sushi_forensics", "location": null, "status": "resolved", "bio": "Moderator of r/sushiforensics." },
            { "platform": "LinkedIn", "username": "sushi_forensics", "url": "https://linkedin.com/in/sushi_forensics", "location": "Tokyo Area, Japan", "status": "resolved", "bio": "Security Researcher at Pi-Labs" },
            { "platform": "Instagram", "username": "sushi_forensics", "url": "https://instagram.com/sushi_forensics", "location": null, "status": "not_found", "bio": "" }
          ]
        }
      },
      source_profile: {
        username: "@sushi_forensics",
        display_name: "Sushi Provenance Forensics",
        description: "肩肘張らずに、本物を。 江戸前寿司の伝統を大切にしながら...",
        website: "sushi.jp",
        join_date: "2024-03-12",
        tweet_source: "nitter"
      }
    };
    setAnalysis(mockData);
    localStorage.setItem('helix_session', JSON.stringify(mockData));
    addLog(`SUCCESS: Simulated environment mapped. country=Japan confidence=88%`);
    showToast("Simulated demo workspace loaded.", "info");
  };

  return (
    <div className="min-h-screen bg-[#070708] text-zinc-300 font-sans antialiased flex flex-col selection:bg-blue-900/50 selection:text-blue-300">
      
      <Header 
        searchQuery={searchQuery} 
        setSearchQuery={setSearchQuery} 
        onResetDemo={() => triggerFallback("Demo Target")} 
        analysis={analysis} 
      />

      <div className="flex-1 flex overflow-hidden">
        
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 flex flex-col overflow-y-auto bg-[#070708] border-r border-[#1f1f23]">
          
          <div className="h-12 border-b border-[#1f1f23] bg-[#09090b] px-6 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-zinc-600" />
              <span className="text-[10px] font-mono tracking-wider text-zinc-400 uppercase">
                WORKSPACE / {activeTab}
              </span>
            </div>
            {analysis && (
              <div className="text-[10px] font-mono text-zinc-500">
                ACTIVE TRACE: <span className="text-blue-400 font-bold">{analysis.filename}</span>
              </div>
            )}
          </div>

          <div className="flex-1 p-6 space-y-6">
            
            {!analysis && (
              <IngestionGateway 
                ingestMode={ingestMode}
                setIngestMode={setIngestMode}
                mediaUrl={mediaUrl}
                setMediaUrl={setMediaUrl}
                onFileUpload={handleFileUpload}
                onLinkSubmit={handleLinkSubmit}
                loading={loading}
                uploadProgress={uploadProgress}
              />
            )}

            {analysis && (
              <>
                {activeTab === 'dashboard' && <Dashboard analysis={analysis} loading={loading} />}
                {activeTab === 'profile' && (
                  <ProfileIntel 
                    analysis={analysis} 
                    textAnalysis={textAnalysis} 
                    captionInput={captionInput}
                    setCaptionInput={setCaptionInput}
                    onLinguisticAnalyze={handleLinguisticAnalyze}
                    textLoading={textLoading}
                  />
                )}
                {activeTab === 'media' && <MediaForensics analysis={analysis} backendUrl={BACKEND_URL} />}
                {activeTab === 'timeline' && (
                  <TimelineAnalyser 
                    analysis={analysis} 
                    selectedTimelineEvent={selectedTimelineEvent}
                    setSelectedTimelineEvent={setSelectedTimelineEvent}
                  />
                )}
                {activeTab === 'network' && (
                  <PropagationNetwork 
                    analysis={analysis} 
                    hoveredNode={hoveredNode}
                    setHoveredNode={setHoveredNode}
                  />
                )}
                {activeTab === 'console' && <Console terminalLogs={terminalLogs} />}
                {activeTab === 'settings' && <Settings backendUrl={BACKEND_URL} />}
                {activeTab === 'trace' && <DisseminationTracker analysis={analysis} backendUrl={BACKEND_URL} />}
              </>
            )}
          </div>
        </main>

        <EvidencePanel 
          analysis={analysis} 
          onTerminateSession={handleTerminateSession} 
          onExportPDF={handleExportPDF}
          onExportCSV={handleExportCSV}
        />

      </div>

      {/* Toast container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <Toast 
              message={t.message} 
              type={t.type} 
              onClose={() => removeToast(t.id)} 
            />
          </div>
        ))}
      </div>

      <div className="fixed inset-0 pointer-events-none opacity-[0.01] overflow-hidden">
        <div className="absolute -top-40 -left-40 w-96 h-96 rounded-full bg-blue-500 blur-[100px]"></div>
      </div>

    </div>
  );
}
