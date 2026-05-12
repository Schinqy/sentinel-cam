"use client";

import React, { useState } from 'react';

interface CameraFeedProps {
  id: string;
  name: string;
  violationType: string;
  streamUrl?: string;
  sourceUrl?: string;
  isPrimary?: boolean;
  isExpanded?: boolean;
  onSettingsClick?: () => void;
  onExpandToggle?: () => void;
  onRoiSaved?: () => void;
  initialRoi?: [number, number, number, number];
}

export default function CameraFeed({ id, name, violationType, streamUrl, sourceUrl, isPrimary, isExpanded, onSettingsClick, onExpandToggle, onRoiSaved, initialRoi }: CameraFeedProps) {
  const [isLoaded, setIsLoaded] = useState(false);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [error, setError] = useState(false);
  const [roi, setRoi] = useState<[number, number, number, number] | null>(initialRoi && initialRoi[2] > 0 ? initialRoi : null);
  const [drawing, setDrawing] = useState(false);
  const [startPoint, setStartPoint] = useState<[number, number] | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');
  
  let displayIp = "No source";
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
    e.preventDefault();
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
      setSaveStatus('saving');
      fetch(`http://127.0.0.1:8005/cameras/${id}/roi`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': 'sentinel-secret-2026'
        },
        body: JSON.stringify(roi)
      })
      .then(res => res.json())
      .then(() => {
        setSaveStatus('saved');
        setIsCalibrating(false);
        if (onRoiSaved) onRoiSaved();
        setTimeout(() => setSaveStatus('idle'), 2000);
      })
      .catch(err => {
        console.error("Error saving zones:", err);
        setSaveStatus('idle');
        setIsCalibrating(false);
      });
    } else {
      setIsCalibrating(false);
    }
  };

  return (
    <div className={`relative glass-card overflow-hidden group border-2 ${isPrimary ? 'border-primary/20' : 'border-white/5'}`}>
      {/* Header - high z-index so it always shows above the feed */}
      <div className="absolute top-0 left-0 right-0 p-2 flex justify-between items-center z-30 bg-gradient-to-b from-black/90 via-black/50 to-transparent pointer-events-none">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full flex-shrink-0 ${isLoaded ? 'bg-success animate-pulse' : error ? 'bg-error' : 'bg-warning animate-pulse'}`} />
          <span className="text-[11px] font-bold uppercase tracking-widest text-white leading-tight">{name}</span>
        </div>
        <div className="px-2 py-0.5 rounded bg-black/60 border border-white/10 flex-shrink-0">
          <span className="text-[10px] font-medium text-primary uppercase">{violationType}</span>
        </div>
      </div>

      {/* Main Feed */}
      <div
        className="aspect-video bg-black flex items-center justify-center relative overflow-hidden"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {/* Scanning overlay when live */}
        {isLoaded && (
          <div className="absolute inset-0 z-20 pointer-events-none overflow-hidden">
            <div className="scanning-line animate-scan" />
          </div>
        )}

        {/* Stream image */}
        {streamUrl && (
          <img 
            src={streamUrl} 
            alt={name} 
            className={`w-full h-full object-cover transition-opacity duration-500 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
            onLoad={() => { setIsLoaded(true); setError(false); }}
            onError={() => { setError(true); setIsLoaded(false); }}
          />
        )}

        {/* Initializing state */}
        {(!isLoaded && !error) && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-900/80 z-10">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-white/40 tracking-wider font-medium uppercase">INITIALIZING...</span>
          </div>
        )}

        {/* Offline state */}
        {error && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-slate-900 z-10">
            <span className="text-2xl">⚠</span>
            <span className="text-xs text-white/40 tracking-wider font-medium uppercase text-center px-4">
              FEED OFFLINE<br/>
              <span className="text-[10px] lowercase text-white/20">check hub connection</span>
            </span>
          </div>
        )}

        {/* ROI Overlay — z-index 25, above feed but below header */}
        {(roi || isCalibrating) && (
          <div
            className={`absolute inset-0 z-25 select-none ${isCalibrating ? 'bg-primary/10 cursor-crosshair' : 'pointer-events-none'}`}
          >
            {/* Instruction hint */}
            {isCalibrating && !drawing && !roi && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="text-white text-[10px] font-bold bg-primary/90 px-3 py-1.5 rounded shadow-lg uppercase tracking-wider animate-bounce">
                  Click &amp; drag to draw detection zone
                </div>
              </div>
            )}
            {/* The ROI box */}
            {roi && (
              <div
                className={`absolute border-2 border-dashed flex items-center justify-center pointer-events-none transition-all ${isCalibrating ? 'border-primary bg-primary/20' : 'border-cyan-400/60 bg-cyan-400/5'}`}
                style={{
                  left: `${roi[0] * 100}%`,
                  top: `${roi[1] * 100}%`,
                  width: `${(roi[2] - roi[0]) * 100}%`,
                  height: `${(roi[3] - roi[1]) * 100}%`,
                }}
              >
                <span className={`text-[8px] font-bold px-1 py-0.5 rounded whitespace-nowrap ${isCalibrating ? 'bg-primary text-white' : 'bg-cyan-400/30 text-cyan-300'}`}>
                  {isCalibrating ? 'DETECTION ZONE' : 'ZONE'}
                </span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer / Controls — visible on hover */}
      <div className="p-2 flex justify-between items-center bg-black/40 backdrop-blur-sm border-t border-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <div className="flex gap-2">
          <button 
            onClick={() => {
              if (isCalibrating) {
                saveZones();
              } else {
                setIsCalibrating(true);
              }
            }}
            className={`px-3 py-1 rounded text-[10px] font-bold transition-all uppercase ${isCalibrating ? 'bg-primary text-white animate-pulse' : 'bg-white/10 hover:bg-white/20 text-white/70'}`}
          >
            {isCalibrating ? (saveStatus === 'saving' ? 'SAVING...' : 'SAVE ZONE') : 'SET ZONE'}
          </button>
          {saveStatus === 'saved' && (
            <span className="text-success text-[10px] font-bold uppercase self-center">Zone Saved!</span>
          )}
          <button 
            onClick={onSettingsClick}
            className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white/70 text-[10px] font-bold transition-all uppercase"
          >
            SETTINGS
          </button>
          <button 
            onClick={onExpandToggle}
            className="px-3 py-1 rounded bg-white/10 hover:bg-white/20 text-white/70 text-[10px] font-bold transition-all uppercase"
          >
            {isExpanded ? 'MINIMIZE' : 'EXPAND'}
          </button>
        </div>
        <div className="text-[10px] text-white/30 font-mono italic">
          {displayIp}
        </div>
      </div>
    </div>
  );
}
