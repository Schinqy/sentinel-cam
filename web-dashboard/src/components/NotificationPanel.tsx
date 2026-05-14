"use client";

import React from 'react';
import { ViolationEvent } from '@/hooks/useSocket';

interface NotificationPanelProps {
  violations: ViolationEvent[];
  onViolationClick: (v: ViolationEvent) => void;
  onViewHistory: () => void;
}

export default function NotificationPanel({ violations, onViolationClick, onViewHistory }: NotificationPanelProps) {
  return (
    <div className="flex flex-col h-full glass-card border border-white/5">
      <div className="p-4 border-b border-white/10 flex justify-between items-center">
        <h2 className="text-xs font-black uppercase tracking-[0.2em] text-white/50">VIOLATION LOG</h2>
        <div className="px-2 py-1 bg-primary/20 text-[10px] font-bold text-primary rounded-full animate-pulse-subtle">
           LIVE
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {violations.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8">
            <div className="w-12 h-12 bg-white/5 rounded-full flex items-center justify-center mb-3">
               <div className="w-2 h-2 bg-white/20 rounded-full" />
            </div>
            <div className="text-[10px] font-bold text-white/20 uppercase tracking-widest leading-loose">
              WAITING FOR EVENTS...<br/>
              SCANNING NODES
            </div>
          </div>
        ) : (
          violations.map((log, index) => (
            <div 
              key={`${log.timestamp}-${index}`} 
              onClick={() => onViolationClick(log)}
              className="p-3 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 transition-all cursor-pointer group"
            >
              <div className="flex justify-between items-start mb-2">
                 <div>
                    <div className="text-[10px] font-black text-error tracking-widest uppercase mb-0.5">{(log.violation || log.type || "VIOLATION").replace('_', ' ')}</div>
                    <div className="text-[9px] font-bold text-white/40 uppercase">{log.cam_id} &bull; {log.timestamp}</div>
                 </div>
                 <div className="text-[10px] font-mono text-success">{Math.round(log.confidence * 100)}%</div>
              </div>
              
              <div className="aspect-video bg-black/40 rounded border border-white/5 overflow-hidden relative mt-2">
                  <img 
                    src={log.image_path ? `http://localhost:8005/${log.image_path}` : `https://images.unsplash.com/photo-1545147986-a9d6f2bb03b5?auto=format&fit=crop&q=80&w=400`} 
                    className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity" 
                    alt="Violation"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = "https://images.unsplash.com/photo-1545147986-a9d6f2bb03b5?auto=format&fit=crop&q=80&w=400";
                    }}
                  />
              </div>
            </div>
          ))
        )}
      </div>
      
      <div className="p-4 border-t border-white/10 text-center">
         <button 
           onClick={onViewHistory}
           className="text-[10px] font-bold text-white/40 hover:text-white/90 transition-colors uppercase tracking-widest w-full py-2 hover:bg-white/5 rounded-md"
         >
            VIEW FULL HISTORY
         </button>
      </div>
    </div>
  );
}
