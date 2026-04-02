"use client";

import React, { useRef, useEffect, useState } from 'react';

interface CameraFeedProps {
  id: string;
  name: string;
  violationType: string;
  streamUrl?: string; // e.g. "http://localhost:8000/video/cam1"
  isPrimary?: boolean;
}

export default function CameraFeed({ id, name, violationType, streamUrl, isPrimary }: CameraFeedProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isCalibrating, setIsCalibrating] = useState(false);
  
  // Simulated connection for now
  useEffect(() => {
    const timer = setTimeout(() => setIsConnected(true), 1500);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className={`relative glass-card overflow-hidden group border-2 ${isPrimary ? 'border-primary/20' : 'border-white/5'}`}>
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 p-3 flex justify-between items-center z-10 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-success animate-pulse' : 'bg-danger'}`} />
          <span className="text-xs font-bold uppercase tracking-widest text-white/90">{name}</span>
        </div>
        <div className="px-2 py-0.5 rounded bg-black/40 border border-white/10">
          <span className="text-[10px] font-medium text-primary uppercase">{violationType}</span>
        </div>
      </div>

      {/* Main Feed Video / Mock */}
      <div className="aspect-video bg-black flex items-center justify-center relative">
        {isConnected ? (
          streamUrl ? (
            <img 
              src={streamUrl} 
              alt={name} 
              className="w-full h-full object-cover"
              onError={(e) => {
                (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1545147986-a9d6f2bb03b5?auto=format&fit=crop&q=80&w=1000'; // Fallback
              }}
            />
          ) : (
            <div className="w-full h-full bg-slate-900 flex items-center justify-center">
               <div className="text-white/20 text-sm italic">Feed active. Waiting for frames...</div>
            </div>
          )
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-white/40 tracking-wider font-medium">CONNECTING...</span>
          </div>
        )}

        {/* Calibration Overlay (Placeholder for now) */}
        {isCalibrating && (
          <div className="absolute inset-0 bg-primary/10 border-2 border-primary/50 cursor-crosshair flex items-center justify-center overflow-hidden">
            <div className="text-white text-[10px] font-bold bg-primary px-2 py-1 rounded shadow-lg animate-bounce">
              DRAW VIOLATION ZONES ({name})
            </div>
          </div>
        )}
      </div>

      {/* Footer / Controls */}
      <div className="p-2 flex justify-between items-center bg-black/20 backdrop-blur-sm border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="flex gap-2">
           <button 
             onClick={() => setIsCalibrating(!isCalibrating)}
             className={`px-3 py-1 rounded text-[10px] font-bold transition-all ${isCalibrating ? 'bg-accent text-white' : 'bg-white/10 hover:bg-white/20 text-white/70'}`}
           >
             {isCalibrating ? 'SAVE ZONES' : 'CALIBRATE'}
           </button>
           <button className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white/70 text-[10px] font-bold transition-all">
             SETTINGS
           </button>
        </div>
        <div className="text-[10px] text-white/40 font-mono">
           192.168.1.{id === '1' ? '45' : id === '2' ? '46' : '47'}
        </div>
      </div>
    </div>
  );
}
