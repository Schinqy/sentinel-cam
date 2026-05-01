"use client";

import React, { useState } from 'react';

interface CameraFeedProps {
  id: string;
  name: string;
  violationType: string;
  streamUrl?: string; // e.g. "http://localhost:8000/video/cam1"
  sourceUrl?: string; // e.g. "http://10.26.15.40/stream"
  isPrimary?: boolean;
  isExpanded?: boolean;
  onSettingsClick?: () => void;
  onExpandToggle?: () => void;
}

export default function CameraFeed({ id, name, violationType, streamUrl, sourceUrl, isPrimary, isExpanded, onSettingsClick, onExpandToggle }: CameraFeedProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [error, setError] = useState(false);
  const [roi, setRoi] = useState<[number, number, number, number] | null>(null);
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<[number, number] | null>(null);
  
  let displayIp = "127.0.0.1";
  try {
    if (sourceUrl) {
      const urlObj = new URL(sourceUrl);
      displayIp = urlObj.hostname;
    }
  } catch (e) {
    if (sourceUrl) displayIp = sourceUrl;
  }

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isCalibrating) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    setStartPoint([x, y]);
    setRoi([x, y, x, y]);
    setDrawing(true);
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isCalibrating || !drawing || !startPoint) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (e.clientY - rect.top) / rect.height));
    setRoi([
      Math.min(startPoint[0], x),
      Math.min(startPoint[1], y),
      Math.max(startPoint[0], x),
      Math.max(startPoint[1], y)
    ]);
  };

  const handleMouseUp = () => {
    if (isCalibrating && drawing) {
      setDrawing(false);
    }
  };

  const saveZones = () => {
    if (roi) {
      fetch(`http://127.0.0.1:8005/cameras/${id}/roi`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': 'sentinel-secret-2026'
        },
        body: JSON.stringify(roi)
      })
      .then(res => res.json())
      .then(data => {
        console.log("ROI updated:", data);
        setIsCalibrating(false);
      })
      .catch(err => console.error("Error saving zones:", err));
    } else {
      setIsCalibrating(false);
    }
  };

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

        {/* Interactive Calibration Overlay */}
        {isCalibrating && (
          <div 
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            className="absolute inset-0 bg-primary/10 border-2 border-primary/30 cursor-crosshair z-30 select-none flex items-center justify-center overflow-hidden"
          >
            {roi ? (
              <div 
                className="absolute border-2 border-dashed border-primary bg-primary/20 backdrop-blur-[1px] flex items-center justify-center pointer-events-none"
                style={{
                  left: `${roi[0] * 100}%`,
                  top: `${roi[1] * 100}%`,
                  width: `${(roi[2] - roi[0]) * 100}%`,
                  height: `${(roi[3] - roi[1]) * 100}%`,
                }}
              >
                <span className="text-white text-[9px] font-bold bg-primary px-1 py-0.5 rounded shadow whitespace-nowrap">
                  ROI DETECT ZONE
                </span>
              </div>
            ) : (
              <div className="text-white text-[10px] font-bold bg-primary/80 px-3 py-1 rounded shadow-lg animate-bounce pointer-events-none select-none uppercase tracking-wider">
                Click & drag to draw ROI
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer / Controls */}
      <div className="p-2 flex justify-between items-center bg-black/20 backdrop-blur-sm border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="flex gap-2">
           <button 
             onClick={() => {
               if (isCalibrating) {
                 saveZones();
               } else {
                 setIsCalibrating(true);
               }
             }}
             className={`px-3 py-1 rounded text-[10px] font-bold transition-all ${isCalibrating ? 'bg-accent text-white' : 'bg-white/10 hover:bg-white/20 text-white/70'}`}
           >
             {isCalibrating ? 'SAVE ZONES' : 'CALIBRATE'}
           </button>
           <button 
             onClick={onSettingsClick}
             className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white/70 text-[10px] font-bold transition-all"
           >
             SETTINGS
           </button>
           <button 
             onClick={onExpandToggle}
             className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white/70 text-[10px] font-bold transition-all"
           >
             {isExpanded ? 'MINIMIZE' : 'EXPAND'}
           </button>
        </div>
        <div className="text-[10px] text-white/40 font-mono italic">
           {displayIp}
        </div>
      </div>
    </div>
  );
}
