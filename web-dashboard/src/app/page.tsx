'use client';

import { useState, useEffect } from 'react';
import CameraFeed from "@/components/CameraFeed";
import NotificationPanel from "@/components/NotificationPanel";
import EvidenceModal from "@/components/EvidenceModal";
import ViolationHistory from "@/components/ViolationHistory";
import { useSocket, ViolationEvent } from "@/hooks/useSocket";

type DashboardView = 'dashboard' | 'history';

export default function Home() {
  const { violations: liveViolations, trafficLight, isConnected } = useSocket('ws://127.0.0.1:8005/ws');
  const [history, setHistory] = useState<ViolationEvent[]>([]);
  const [cameras, setCameras] = useState<any[]>([]);
  const [selectedViolation, setSelectedViolation] = useState<ViolationEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [activeView, setActiveView] = useState<DashboardView>('dashboard');
  const [settingsCamera, setSettingsCamera] = useState<any | null>(null);
  const [diagnostics, setDiagnostics] = useState<any | null>(null);
  const [settingsUrl, setSettingsUrl] = useState('');
  const [settingsName, setSettingsName] = useState('');
  const [expandedCamId, setExpandedCamId] = useState<string | null>(null);
  const [showTestMode, setShowTestMode] = useState(false);
  const [showAddCamera, setShowAddCamera] = useState(false);
  const [newCamId, setNewCamId] = useState('');
  const [newCamName, setNewCamName] = useState('');
  const [newCamUrl, setNewCamUrl] = useState('');
  const [addCamError, setAddCamError] = useState('');

  const fetchDiagnostics = () => {
    fetch('http://127.0.0.1:8005/diagnostics', {
      headers: { 'X-API-Key': 'sentinel-secret-2026' }
    })
      .then(res => res.json())
      .then(data => setDiagnostics(data))
      .catch(err => console.error("Error fetching diagnostics:", err));
  };

  useEffect(() => {
    setMounted(true);
    // Fetch History
    fetch('http://127.0.0.1:8005/violations', {
      headers: { 'X-API-Key': 'sentinel-secret-2026' }
    })
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error("Error fetching history:", err));

    // Fetch Cameras
    fetch('http://127.0.0.1:8005/cameras', {
      headers: { 'X-API-Key': 'sentinel-secret-2026' }
    })
      .then(res => res.json())
      .then(data => setCameras(data))
      .catch(err => console.error("Error fetching cameras:", err));

    fetchDiagnostics();
    const iv = setInterval(fetchDiagnostics, 5000);
    return () => clearInterval(iv);
  }, []);

  const handleViolationClick = (v: ViolationEvent) => {
    setSelectedViolation(v);
    setIsModalOpen(true);
  };

  const allViolations = [...liveViolations, ...history].filter((v, i, a) => 
    a.findIndex(t => t.timestamp === v.timestamp && t.cam_id === v.cam_id) === i
  );

  if (!mounted) return null; // Or a skeleton/loading state

  return (
    <main className="flex-1 flex flex-col p-4 gap-4 h-full max-w-[1600px] mx-auto w-full overflow-hidden">
      {/* Header Section */}
      <header className="flex justify-between items-end pb-2 border-b border-white/10 shrink-0">
        <div className="cursor-pointer" onClick={() => setActiveView('dashboard')}>
          <h1 className="text-xl font-black italic tracking-tighter text-white uppercase">
            A.T.V.D. <span className="text-primary">SYSTEM</span>
          </h1>
          <p className="text-[10px] font-bold text-white/40 uppercase tracking-[0.3em]">
            Automated Traffic Violation Detection v1.0
          </p>
        </div>
        <div className="flex gap-4">
          <div className="text-right border-r border-white/10 pr-4">
             <div className="text-[10px] font-bold text-white/40 uppercase tracking-widest">TRAFFIC LIGHT</div>
             <div className={`text-[11px] font-black uppercase ${trafficLight === 'RED' ? 'text-error animate-pulse-subtle' : trafficLight === 'GREEN' ? 'text-success' : 'text-warning'}`}>
               {trafficLight === 'RED' ? '🛑 RED' : trafficLight === 'GREEN' ? '🟢 GREEN' : '🟡 UNKNOWN'}
             </div>
          </div>
          <div className="text-right">
             <div className="text-[10px] font-bold text-white/40 uppercase tracking-widest">SYSTEM STATUS</div>
             <div className={`text-[10px] font-bold uppercase ${isConnected ? 'text-success animate-pulse-subtle' : 'text-error'}`}>
               {isConnected ? 'ALL NODES ONLINE' : 'HUB DISCONNECTED'}
             </div>
          </div>
          <div className="text-right">
             <div className="text-[10px] font-bold text-white/40 uppercase tracking-widest">LAST EVENT</div>
              <div className="text-[10px] font-bold text-white/80 uppercase">
                {allViolations.length > 0 ? allViolations[0].timestamp : '--:--:--'}
              </div>
          </div>
          <div className="flex items-center gap-2">
             <button
               onClick={() => { setNewCamId(''); setNewCamName(''); setNewCamUrl(''); setAddCamError(''); setShowAddCamera(true); }}
               className="px-3 py-1 rounded bg-success/20 hover:bg-success/30 text-success border border-success/40 text-[10px] font-bold uppercase transition-all"
             >
               + Add Camera
             </button>
             <button
               onClick={() => setShowTestMode(!showTestMode)}
               className={`px-3 py-1 rounded border text-[10px] font-bold uppercase transition-all ${showTestMode ? 'bg-primary text-white border-primary' : 'bg-transparent text-white/40 border-white/20 hover:text-white'}`}
             >
               {showTestMode ? 'TEST SUITE: ON' : 'TEST SUITE: OFF'}
             </button>
          </div>
        </div>
      </header>

      {showTestMode && (
        <div className="bg-primary/5 border border-primary/20 rounded p-3 flex flex-wrap gap-3 items-center justify-between shrink-0 animate-fade-in bg-slate-950">
          <div className="flex flex-col">
            <span className="text-xs font-black italic text-primary uppercase">Manual Test Triggers</span>
            <span className="text-[9px] font-medium text-white/40 uppercase">Trigger artificial violation events for verification</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button 
              onClick={() => {
                fetch('http://127.0.0.1:8005/test/trigger-violation', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sentinel-secret-2026' },
                  body: JSON.stringify({ cam_id: 'cam1', v_type: 'Illegal Parking' })
                })
                .then(res => res.json())
                .catch(err => console.error(err));
              }}
              className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 text-[10px] font-bold uppercase transition-all"
            >
              Simulate Cam1 Violation
            </button>
            <button 
              onClick={() => {
                fetch('http://127.0.0.1:8005/test/trigger-violation', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sentinel-secret-2026' },
                  body: JSON.stringify({ cam_id: 'cam2', v_type: 'Red Robot' })
                })
                .then(res => res.json())
                .catch(err => console.error(err));
              }}
              className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 text-[10px] font-bold uppercase transition-all"
            >
              Simulate Cam2 Violation
            </button>
            <button 
              onClick={() => {
                fetch('http://127.0.0.1:8005/test/trigger-violation', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sentinel-secret-2026' },
                  body: JSON.stringify({ cam_id: 'cam3', v_type: 'Stop Line' })
                })
                .then(res => res.json())
                .catch(err => console.error(err));
              }}
              className="px-3 py-1.5 rounded bg-red-500/20 hover:bg-red-500/30 text-red-300 border border-red-500/40 text-[10px] font-bold uppercase transition-all"
            >
              Simulate Cam3 Violation
            </button>
          </div>
        </div>
      )}

      {activeView === 'dashboard' ? (
        /* Grid Section */
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden min-h-0">
          
          {/* Left & Center: Multi-Feed Monitor */}
          <div className="lg:col-span-3 flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar">
            
            {expandedCamId ? (
              <div className="flex-1 min-w-0">
                {cameras.filter(c => c.id === expandedCamId).map(cam => (
                  <CameraFeed 
                    key={cam.id}
                    id={cam.id} 
                    name={cam.name} 
                    violationType={cam.id === 'cam1' ? "Illegal Parking" : cam.id === 'cam2' ? "Red Robot" : "Stop Line"} 
                    isPrimary={true}
                    isExpanded={true}
                    streamUrl={`http://127.0.0.1:8005/video/${cam.id}`}
                    sourceUrl={cam.url}
                    initialRoi={[cam.roi_x1, cam.roi_y1, cam.roi_x2, cam.roi_y2]}
                    onExpandToggle={() => setExpandedCamId(null)}
                    onSettingsClick={() => {
                      setSettingsCamera(cam);
                      setSettingsUrl(cam.url);
                      setSettingsName(cam.name);
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className={`grid gap-4 ${cameras.length === 1 ? 'grid-cols-1' : cameras.length === 2 ? 'grid-cols-1 xl:grid-cols-2' : 'grid-cols-1 xl:grid-cols-2'}`}>
                {cameras.map((cam, idx) => (
                  <div key={cam.id} className={idx === 0 && cameras.length > 2 ? 'xl:col-span-1 xl:row-span-2' : ''}>
                    <CameraFeed 
                      id={cam.id} 
                      name={cam.name} 
                      violationType={cam.id === 'cam1' ? "Illegal Parking" : cam.id === 'cam2' ? "Red Robot" : "Stop Line"} 
                      isPrimary={idx === 0}
                      streamUrl={`http://127.0.0.1:8005/video/${cam.id}`}
                      sourceUrl={cam.url}
                      initialRoi={[cam.roi_x1, cam.roi_y1, cam.roi_x2, cam.roi_y2]}
                      onExpandToggle={() => setExpandedCamId(cam.id)}
                      onSettingsClick={() => {
                        setSettingsCamera(cam);
                        setSettingsUrl(cam.url);
                        setSettingsName(cam.name);
                      }}
                    />
                  </div>
                ))}
                {cameras.length === 0 && (
                   <div className="flex flex-col items-center justify-center py-20 bg-white/5 border border-dashed border-white/10 rounded-xl">
                      <div className="text-white/20 text-xs font-bold uppercase tracking-widest">No Cameras Configured</div>
                   </div>
                )}
              </div>
            )}

            {/* Quick Stats / Environment Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass-card p-4 border border-white/5">
                  <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest mb-1">TOTAL CITATIONS</div>
                  <div className="text-2xl font-black text-white italic">{allViolations.length}</div>
                  <div className="h-1 w-full bg-white/5 rounded-full mt-2 overflow-hidden">
                     <div className="bg-primary h-full w-[100%]" />
                  </div>
               </div>
               <div className="glass-card p-4 border border-white/5">
                  <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest mb-1">DETECTION RATE</div>
                  <div className="text-2xl font-black text-white italic">{allViolations.length > 0 ? '100%' : '0%'}</div>
                  <div className="h-1 w-full bg-white/5 rounded-full mt-2 overflow-hidden">
                     <div className="bg-success h-full w-[100%]" />
                  </div>
               </div>
               <div className="glass-card p-4 border border-white/5">
                  <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest mb-1">SCALE CALIBRATION</div>
                  <div className="text-2xl font-black text-white italic">1:24</div>
                  <div className="text-[9px] font-medium text-white/20 mt-2 uppercase tracking-wide">Model Scale Mode Active</div>
               </div>
            </div>
          </div>

          {/* Right Sidebar: Notification Panel */}
          <div className="lg:col-span-1 h-full min-h-0 flex flex-col">
             <NotificationPanel 
               violations={allViolations} 
               onViolationClick={handleViolationClick}
               onViewHistory={() => setActiveView('history')}
             />
          </div>
        </div>
      ) : (
        /* History View */
        <div className="flex-1 min-h-0">
          <ViolationHistory 
            violations={allViolations} 
            onViolationClick={handleViolationClick}
            onBack={() => setActiveView('dashboard')}
          />
        </div>
      )}

      <EvidenceModal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        violationData={selectedViolation}
        imageUrl={selectedViolation?.image_path ? `http://127.0.0.1:8005/${selectedViolation.image_path}` : null}
      />

      {settingsCamera && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-lg w-full p-6 border-2 border-primary/20 flex flex-col gap-4 animate-fade-in bg-slate-950">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <h3 className="text-sm font-black italic text-white tracking-wider uppercase">
                DIAGNOSTICS & SETTINGS: {settingsCamera.id}
              </h3>
              <button 
                onClick={() => setSettingsCamera(null)}
                className="text-xs text-white/50 hover:text-white transition-colors uppercase font-bold"
              >
                Close
              </button>
            </div>
            
            <div className="flex flex-col gap-2 bg-black/40 p-3 rounded border border-white/5 font-mono text-[10px] text-white/60">
              <div className="flex justify-between">
                <span>Disk Free Space:</span>
                <span className="text-white font-bold">{diagnostics?.disk_free_gb ?? '--'} GB</span>
              </div>
              <div className="flex justify-between">
                <span>CPU Load:</span>
                <span className="text-white font-bold">{diagnostics?.cpu_load ?? 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span>Hub Active WS:</span>
                <span className="text-white font-bold">{diagnostics?.active_connections ?? 0}</span>
              </div>
              <div className="border-t border-white/10 pt-1 mt-1">
                <span className="block mb-1">Camera Statuses:</span>
                {diagnostics?.cameras?.map((c: any) => (
                  <div key={c.id} className="flex justify-between pl-2">
                    <span>{c.name || c.id}:</span>
                    <span className={c.status === 'ONLINE' ? 'text-success font-bold' : 'text-error font-bold'}>
                      {c.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex flex-col gap-3 mt-1">
              <div>
                <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest block mb-1">
                  Camera Display Name
                </label>
                <input 
                  type="text" 
                  value={settingsName} 
                  onChange={(e) => setSettingsName(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 text-white rounded p-2 text-xs focus:outline-none focus:border-primary/50 transition-colors"
                />
              </div>
              <div>
                <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest block mb-1">
                  Stream URL (IP)
                </label>
                <input 
                  type="text" 
                  value={settingsUrl} 
                  onChange={(e) => setSettingsUrl(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 text-white rounded p-2 text-xs focus:outline-none focus:border-primary/50 transition-colors"
                />
              </div>
              <button 
                onClick={() => {
                  fetch(`http://127.0.0.1:8005/cameras/${settingsCamera.id}/config`, {
                    method: 'POST',
                    headers: { 
                      'Content-Type': 'application/json',
                      'X-API-Key': 'sentinel-secret-2026'
                    },
                    body: JSON.stringify({
                      name: settingsName,
                      url: settingsUrl
                    })
                  })
                  .then(res => res.json())
                  .then(() => {
                    fetch('http://127.0.0.1:8005/cameras', {
                      headers: { 'X-API-Key': 'sentinel-secret-2026' }
                    })
                      .then(res => res.json())
                      .then(data => setCameras(data));
                    setSettingsCamera(null);
                  })
                  .catch(err => console.error("Error updating camera URL:", err));
                }}
                className="w-full py-2 bg-primary hover:bg-primary-dark font-black italic uppercase tracking-wider text-white text-xs rounded transition-all mt-2 cursor-pointer"
              >
                Update Camera Config
              </button>
              
              <button 
                onClick={() => {
                  if (confirm(`Are you sure you want to delete ${settingsCamera.id}?`)) {
                    fetch(`http://127.0.0.1:8005/cameras/${settingsCamera.id}`, {
                      method: 'DELETE',
                      headers: { 'X-API-Key': 'sentinel-secret-2026' }
                    })
                    .then(() => {
                      fetch('http://127.0.0.1:8005/cameras', {
                        headers: { 'X-API-Key': 'sentinel-secret-2026' }
                      })
                        .then(res => res.json())
                        .then(data => setCameras(data));
                      setSettingsCamera(null);
                      if (expandedCamId === settingsCamera.id) setExpandedCamId(null);
                    });
                  }
                }}
                className="w-full py-2 bg-error/10 hover:bg-error/20 border border-error/20 text-error font-bold uppercase tracking-wider text-[10px] rounded transition-all cursor-pointer"
              >
                Delete Camera Node
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Add Camera Modal */}
      {showAddCamera && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="glass-card max-w-md w-full p-6 border-2 border-success/20 flex flex-col gap-4 animate-fade-in bg-slate-950">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <h3 className="text-sm font-black italic text-white tracking-wider uppercase">Add New Camera Node</h3>
              <button onClick={() => setShowAddCamera(false)} className="text-xs text-white/50 hover:text-white uppercase font-bold">Close</button>
            </div>
            <p className="text-[10px] text-white/40 uppercase tracking-wide">Enter the details for the new ESP32-CAM node. The stream URL is the IP address of the camera on your WiFi network.</p>
            <div className="flex flex-col gap-3">
              <div>
                <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest block mb-1">Camera ID <span className="text-white/20">(unique, e.g. cam4)</span></label>
                <input type="text" value={newCamId} onChange={e => setNewCamId(e.target.value)} placeholder="cam4"
                  className="w-full bg-black/40 border border-white/10 text-white rounded p-2 text-xs focus:outline-none focus:border-success/50 transition-colors" />
              </div>
              <div>
                <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest block mb-1">Display Name</label>
                <input type="text" value={newCamName} onChange={e => setNewCamName(e.target.value)} placeholder="West Intersection"
                  className="w-full bg-black/40 border border-white/10 text-white rounded p-2 text-xs focus:outline-none focus:border-success/50 transition-colors" />
              </div>
              <div>
                <label className="text-[10px] font-bold text-white/40 uppercase tracking-widest block mb-1">Stream URL <span className="text-white/20">(ESP32 IP address)</span></label>
                <input type="text" value={newCamUrl} onChange={e => setNewCamUrl(e.target.value)} placeholder="http://192.168.1.48/stream"
                  className="w-full bg-black/40 border border-white/10 text-white rounded p-2 text-xs focus:outline-none focus:border-success/50 transition-colors" />
              </div>
              {addCamError && <p className="text-error text-[10px] font-bold">{addCamError}</p>}
              <button
                onClick={() => {
                  if (!newCamId.trim() || !newCamUrl.trim()) { setAddCamError('Camera ID and URL are required.'); return; }
                  fetch('http://127.0.0.1:8005/cameras', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-API-Key': 'sentinel-secret-2026' },
                    body: JSON.stringify({ id: newCamId.trim(), name: newCamName.trim() || newCamId.trim(), url: newCamUrl.trim() })
                  })
                  .then(res => res.json())
                  .then(data => {
                    if (data.status === 'success') {
                      fetch('http://127.0.0.1:8005/cameras', { headers: { 'X-API-Key': 'sentinel-secret-2026' } })
                        .then(res => res.json()).then(d => setCameras(d));
                      setShowAddCamera(false);
                    } else {
                      setAddCamError(data.detail || 'Failed to add camera. Is the Hub running?');
                    }
                  })
                  .catch(() => setAddCamError('Cannot connect to Hub. Make sure it is running.'));
                }}
                className="w-full py-2 bg-success/20 hover:bg-success/30 border border-success/30 text-success font-black italic uppercase tracking-wider text-xs rounded transition-all cursor-pointer"
              >
                Add Camera to System
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
