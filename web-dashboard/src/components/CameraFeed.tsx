"use client";

import React, { useState } from 'react';

interface CameraFeedProps {
  id: string;
  name: string;
  violationType: string;
  streamUrl?: string; // e.g. "http://localhost:8000/video/cam1"
  isPrimary?: boolean;
}

export default function CameraFeed({ id, name, violationType, streamUrl, isPrimary }: CameraFeedProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [error, setError] = useState(false);
  
  const ipSuffix = id.replace('cam', '');

  return (
    <div className={`relative glass-card overflow-hidden group border-2 ${isPrimary ? 'border-primary/20' : 'border-white/5'}`}>
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 p-3 flex justify-between items-center z-10 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isLoaded ? 'bg-success animate-pulse' : error ? 'bg-error' : 'bg-warning'}`} />
          <span className="text-xs font-bold uppercase tracking-widest text-white/90">{name}</span>
        </div>
        <div className="px-2 py-0.5 rounded bg-black/40 border border-white/10">
          <span className="text-[10px] font-medium text-primary uppercase">{violationType}</span>
        </div>
      </div>

      {/* Main Feed Video / MJPEG Stream */}
      <div className="aspect-video bg-black flex items-center justify-center relative overflow-hidden">
        {isLoaded && <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden">
            <div className="scanning-line animate-scan" />
        </div>}
        
        {streamUrl ? (
          <img 
            src={streamUrl} 
            alt={name} 
            className={`w-full h-full object-cover transition-opacity duration-500 ${isLoaded ? 'opacity-100' : 'opacity-0'} ${isPrimary ? 'animate-glow' : ''}`}
            onLoad={() => {
              setIsLoaded(true);
              setError(false);
            }}
            onError={() => {
              setError(true);
              setIsLoaded(false);
            }}
          />
        ) : null}

        {(!isLoaded && !error) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-900/50">
            <div className="scanning-line animate-scan" />
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-white/40 tracking-wider font-medium uppercase">INITIALIZING...</span>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-900">
            <div className="text-error text-2xl">⚠️</div>
            <span className="text-xs text-white/40 tracking-wider font-medium uppercase text-center px-4">
              FEED OFFLINE<br/>
              <span className="text-[10px] lowercase text-white/20">check hub connection</span>
            </span>
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
        <div className="text-[10px] text-white/40 font-mono italic">
           192.168.1.{44 + parseInt(ipSuffix || '1')}
        </div>
      </div>
    </div>
  );
}
