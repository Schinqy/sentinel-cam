"use client";

import React, { useState } from 'react';

interface ViolationLog {
  id: string;
  type: string;
  cam_id: string;
  timestamp: string;
  confidence: number;
  image?: string;
}

export default function NotificationPanel() {
  const [logs] = useState<ViolationLog[]>([
    { id: '1', type: 'ILLEGAL PARKING', cam_id: 'CAM 1', timestamp: '10:45:22', confidence: 0.94 },
    { id: '2', type: 'RED ROBOT', cam_id: 'CAM 2', timestamp: '10:46:10', confidence: 0.88 },
    { id: '3', type: 'STOP LINE', cam_id: 'CAM 3', timestamp: '10:47:05', confidence: 0.91 },
  ]);

  return (
    <div className="flex flex-col h-full glass-card border border-white/5">
      <div className="p-4 border-b border-white/10 flex justify-between items-center">
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white/50">VIOLATION LOG</h2>
        <div className="px-2 py-1 bg-primary/20 text-[10px] font-bold text-primary rounded-full">
           LIVE
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {logs.map((log) => (
          <div key={log.id} className="p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-all cursor-pointer group">
            <div className="flex justify-between items-start mb-2">
               <div>
                  <div className="text-[10px] font-black text-danger tracking-widest uppercase mb-0.5">{log.type}</div>
                  <div className="text-[9px] font-bold text-white/40 uppercase">{log.cam_id} &bull; {log.timestamp}</div>
               </div>
               <div className="text-[10px] font-mono text-success">{Math.round(log.confidence * 100)}%</div>
            </div>
            
            {/* Snapshot Placeholder */}
            <div className="aspect-video bg-black/40 rounded border border-white/5 overflow-hidden relative">
               <div className="absolute inset-0 flex items-center justify-center text-[10px] text-white/20 italic">
                  SNAPSHOT_{log.id}.JPG
               </div>
               <img 
                 src={`https://images.unsplash.com/photo-1545147986-a9d6f2bb03b5?auto=format&fit=crop&q=80&w=200`} 
                 className="w-full h-full object-cover opacity-50 group-hover:opacity-100 transition-opacity" 
                 alt="Violation"
               />
            </div>
          </div>
        ))}
      </div>
      
      <div className="p-4 border-t border-white/10 text-center">
         <button className="text-[10px] font-bold text-white/40 hover:text-white/90 transition-colors uppercase tracking-widest">
            VIEW HISTORY
         </button>
      </div>
    </div>
  );
}
