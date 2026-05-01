'use client';

import { useState, useEffect } from 'react';
import CameraFeed from "@/components/CameraFeed";
import NotificationPanel from "@/components/NotificationPanel";
import EvidenceModal from "@/components/EvidenceModal";
import ViolationHistory from "@/components/ViolationHistory";
import { useSocket, ViolationEvent } from "@/hooks/useSocket";

type DashboardView = 'dashboard' | 'history';

export default function Home() {
  const { violations: liveViolations, isConnected } = useSocket('ws://127.0.0.1:8005/ws');
  const [history, setHistory] = useState<ViolationEvent[]>([]);
  const [selectedViolation, setSelectedViolation] = useState<ViolationEvent | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [activeView, setActiveView] = useState<DashboardView>('dashboard');

  useEffect(() => {
    setMounted(true);
    // Fetch History
    fetch('http://127.0.0.1:8005/violations', {
      headers: { 'X-API-Key': 'sentinel-secret-2026' }
    })
      .then(res => res.json())
      .then(data => setHistory(data))
      .catch(err => console.error("Error fetching history:", err));
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
            SENTINEL<span className="text-primary">CAM</span>
          </h1>
          <p className="text-[10px] font-bold text-white/40 uppercase tracking-[0.3em]">
            AI Traffic Enforcement System v1.0
          </p>
        </div>
        <div className="flex gap-4">
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
        </div>
      </header>

      {activeView === 'dashboard' ? (
        /* Grid Section */
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 overflow-hidden min-h-0">
          
          {/* Left & Center: Multi-Feed Monitor */}
          <div className="lg:col-span-3 flex flex-col gap-4 overflow-y-auto pr-2 custom-scrollbar">
            
            <div className="flex gap-4 flex-col xl:flex-row">
              {/* Primary Focus: Camera 1 */}
              <div className="flex-[2] min-w-0">
                <CameraFeed 
                  id="cam1" 
                  name="North Intersection" 
                  violationType="Illegal Parking" 
                  isPrimary={true}
                  streamUrl="http://127.0.0.1:8005/video/cam1"
                />
              </div>

              {/* Context Feeds Stack */}
              <div className="flex-1 flex flex-col gap-4 min-w-0">
                 <CameraFeed 
                   id="cam2" 
                   name="East Junction" 
                   violationType="Red Robot" 
                   streamUrl="http://127.0.0.1:8005/video/cam2"
                 />
                 <CameraFeed 
                   id="cam3" 
                   name="South Crosswalk" 
                   violationType="Stop Line" 
                   streamUrl="http://127.0.0.1:8005/video/cam3"
                 />
              </div>
            </div>

            {/* Quick Stats / Environment Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="glass-card p-4 border border-white/5">
                  <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest mb-1">TOTAL CITATIONS</div>
                  <div className="text-2xl font-black text-white italic">{142 + allViolations.length}</div>
                  <div className="h-1 w-full bg-white/5 rounded-full mt-2 overflow-hidden">
                     <div className="bg-primary h-full w-[65%]" />
                  </div>
               </div>
               <div className="glass-card p-4 border border-white/5">
                  <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest mb-1">DETECTION RATE</div>
                  <div className="text-2xl font-black text-white italic">98.4%</div>
                  <div className="h-1 w-full bg-white/5 rounded-full mt-2 overflow-hidden">
                     <div className="bg-success h-full w-[95%]" />
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
    </main>
  );
}
