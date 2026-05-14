"use client";

import React from 'react';

interface EvidenceModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string | null;
  violationData: any;
}

export default function EvidenceModal({ isOpen, onClose, imageUrl, violationData }: EvidenceModalProps) {
  const [isExporting, setIsExporting] = React.useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm">
      <div className="relative max-w-4xl w-full glass-card border border-white/10 overflow-hidden animate-in fade-in zoom-in duration-200">
        <div className="p-6 border-b border-white/10 flex justify-between items-end bg-gradient-to-b from-white/10 to-transparent">
          <div>
            <h2 className="text-[10px] font-black text-primary tracking-[0.3em] uppercase mb-2">VIOLATION EVIDENCE</h2>
            <div className="flex items-center gap-4">
               <div className="bg-white px-4 py-2 rounded-sm border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)]">
                  <span className="text-2xl font-black text-black tracking-tighter font-mono">
                    {violationData?.plate_number || 'SCANNING...'}
                  </span>
               </div>
               <div>
                  <div className="text-[10px] font-bold text-white/60 uppercase">{violationData?.violation?.replace('_', ' ')}</div>
                  <div className="text-[10px] font-mono text-white/40">{violationData?.cam_id} &bull; {violationData?.timestamp}</div>
               </div>
            </div>
          </div>
          <div className="text-right flex flex-col items-end gap-2">
             <button 
                onClick={onClose}
                className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/20 flex items-center justify-center text-white/60 hover:text-white transition-all mb-2"
             >
                &times;
             </button>
             <div className="text-[10px] font-bold text-white/40 uppercase">OCR CONFIDENCE</div>
             <div className="text-xl font-black text-success font-mono">{Math.round((violationData?.confidence || 0.98) * 100)}%</div>
          </div>
        </div>

        <div className="p-2 bg-black/40">
          {imageUrl ? (
            <img 
              src={imageUrl} 
              alt="Evidence" 
              className="w-full h-auto rounded border border-white/10"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.src = "https://images.unsplash.com/photo-1545147986-a9d6f2bb03b5?auto=format&fit=crop&q=80&w=800";
              }}
            />
          ) : (
            <div className="aspect-video flex items-center justify-center bg-white/5 text-white/20 text-xs uppercase tracking-widest">
              IMAGE NOT FOUND
            </div>
          )}
        </div>

        <div className="p-4 flex gap-4 justify-end">
            <button 
                onClick={onClose}
                className="px-6 py-2 bg-white/5 hover:bg-white/10 text-[10px] font-bold text-white/60 uppercase tracking-widest rounded transition-all"
            >
                CLOSE
            </button>
            <button 
              onClick={async () => {
                setIsExporting(true);
                try {
                  const res = await fetch('http://127.0.0.1:8005/api/generate-challan', {
                    method: 'POST',
                    headers: { 
                      'Content-Type': 'application/json',
                      'X-API-Key': 'sentinel-secret-2026'
                    },
                    body: JSON.stringify({ ...violationData, image_path: imageUrl })
                  });
                  const data = await res.json();
                  if (data.status === 'success') {
                    const downloadUrl = `http://127.0.0.1:8005${data.pdf_url}`;
                    window.open(downloadUrl, '_blank');
                  } else {
                    alert("Failed to generate citation.");
                  }
                } catch (e) {
                  console.error(e);
                  alert("Error generating citation.");
                } finally {
                  setIsExporting(false);
                }
              }}
              disabled={isExporting}
              className={`px-6 py-2 bg-primary/20 hover:bg-primary/40 text-[10px] font-bold text-primary uppercase tracking-widest rounded transition-all border border-primary/20 ${isExporting ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                {isExporting ? 'GENERATING...' : 'EXPORT CITATION'}
            </button>
        </div>
      </div>
      
      {/* Background click to close */}
      <div className="absolute inset-0 -z-10" onClick={onClose}></div>
    </div>
  );
}
