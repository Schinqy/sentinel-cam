"use client";

import React, { useState } from 'react';
import { ViolationEvent } from '@/hooks/useSocket';

interface ViolationHistoryProps {
  violations: ViolationEvent[];
  onViolationClick: (v: ViolationEvent) => void;
  onBack: () => void;
}

export default function ViolationHistory({ violations, onViolationClick, onBack }: ViolationHistoryProps) {
  const [filter, setFilter] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [isDeleting, setIsDeleting] = useState(false);

  const filteredViolations = violations.filter(v => 
    v.cam_id.toLowerCase().includes(filter.toLowerCase()) ||
    (v.violation || v.type || '').toLowerCase().includes(filter.toLowerCase())
  );

  const toggleSelectAll = () => {
    if (selectedIds.length === filteredViolations.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredViolations.map(v => v.id!).filter(id => id !== undefined));
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const deleteSingle = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm("Delete this record permanently?")) return;
    
    setIsDeleting(true);
    try {
      const res = await fetch(`http://127.0.0.1:8005/api/violations/${id}`, {
        method: 'DELETE',
        headers: { 'X-API-Key': 'sentinel-secret-2026' }
      });
      if (res.ok) {
        // We'd ideally call a refresh function passed from parent, 
        // but for now, the user can refresh or the parent will update.
        // In page.tsx, we should have a way to refresh.
        window.location.reload(); // Simple sync for now
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsDeleting(false);
    }
  };

  const deleteBulk = async () => {
    if (!confirm(`Delete ${selectedIds.length} records permanently?`)) return;
    
    setIsDeleting(true);
    try {
      const res = await fetch(`http://127.0.0.1:8005/api/violations/delete-multiple`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-API-Key': 'sentinel-secret-2026' 
        },
        body: JSON.stringify({ ids: selectedIds })
      });
      if (res.ok) {
        window.location.reload();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsDeleting(false);
    }
  };


  return (
    <div className="flex flex-col h-full glass-card border border-white/5 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Table Header */}
      <div className="p-6 border-b border-white/10 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-3 mb-1">
             <button 
               onClick={onBack}
               className="p-2 hover:bg-white/5 rounded-full transition-colors group"
             >
               <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-white/40 group-hover:text-primary transition-colors"><path d="m15 18-6-6 6-6"/></svg>
             </button>
             <h2 className="text-xl font-black italic tracking-tighter text-white">
               HISTORICAL <span className="text-primary translate-y-[1px] inline-block">ENFORCEMENT</span> LOG
             </h2>
          </div>
          <p className="text-[10px] font-bold text-white/40 uppercase tracking-[0.3em] ml-11">
            Archive of all captured traffic violations
          </p>
        </div>

        <div className="flex items-center gap-4 w-full md:w-auto">
            {selectedIds.length > 0 && (
              <button 
                onClick={deleteBulk}
                disabled={isDeleting}
                className="px-4 py-2 bg-error/20 hover:bg-error/30 text-error border border-error/40 text-[10px] font-bold uppercase tracking-widest rounded transition-all animate-in fade-in zoom-in"
              >
                DELETE SELECTED ({selectedIds.length})
              </button>
            )}
           <div className="relative flex-1 md:w-64">
              <input 
                type="text" 
                placeholder="FILTER BY CAM OR TYPE..."
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-[10px] font-bold tracking-widest text-white placeholder:text-white/20 focus:outline-none focus:border-primary/50 transition-all"
              />
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="text-white/20"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              </div>
           </div>
        </div>
      </div>

      {/* Table Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-white/5 bg-white/[0.02]">
              <th className="px-6 py-4 w-10">
                <input 
                  type="checkbox" 
                  checked={selectedIds.length === filteredViolations.length && filteredViolations.length > 0}
                  onChange={toggleSelectAll}
                  className="w-4 h-4 rounded border-white/10 bg-black/40 accent-primary cursor-pointer"
                />
              </th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest">Timestamp</th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest">Camera ID</th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest">Plate Number</th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest">Violation Type</th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest">Confidence</th>
              <th className="px-6 py-4 text-[10px] font-black text-white/40 uppercase tracking-widest text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {filteredViolations.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-20 text-center">
                   <div className="text-[10px] font-bold text-white/20 uppercase tracking-widest">
                     NO MATCHING RECORDS FOUND
                   </div>
                </td>
              </tr>
            ) : (
              filteredViolations.map((v, i) => (
                <tr 
                  key={`${v.timestamp}-${i}`} 
                  className={`hover:bg-white/[0.03] transition-colors group cursor-pointer ${selectedIds.includes(v.id!) ? 'bg-primary/5' : ''}`}
                  onClick={() => onViolationClick(v)}
                >
                  <td className="px-6 py-4" onClick={(e) => e.stopPropagation()}>
                    <input 
                      type="checkbox" 
                      checked={selectedIds.includes(v.id!)}
                      onChange={() => toggleSelect(v.id!)}
                      className="w-4 h-4 rounded border-white/10 bg-black/40 accent-primary cursor-pointer"
                    />
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[11px] font-mono text-white/80">{v.timestamp}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-black text-white px-2 py-1 bg-white/5 rounded-md border border-white/5 uppercase tracking-tighter">
                      {v.cam_id}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-[10px] font-mono text-white/60">{v.plate_number || '---'}</span>
                  </td>
                  <td className="px-6 py-4 font-bold text-[10px] text-error uppercase tracking-widest">
                    {(v.violation || v.type || "VIOLATION").replace('_', ' ')}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                       <div className="w-16 h-1 bg-white/5 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-success transition-all duration-1000" 
                            style={{ width: `${v.confidence * 100}%` }}
                          />
                       </div>
                       <span className="text-[10px] font-mono text-success">{Math.round(v.confidence * 100)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex justify-end gap-2 items-center">
                      <button 
                        onClick={(e) => deleteSingle(e, v.id!)}
                        className="p-2 hover:bg-error/20 text-white/20 hover:text-error rounded transition-all"
                        title="Delete record"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
                      </button>
                      <button className="px-3 py-1 bg-primary/10 border border-primary/20 rounded text-[9px] font-black italic text-primary uppercase tracking-tighter hover:bg-primary/20 transition-all">
                        Review
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-white/5 bg-black/20 flex justify-between items-center">
         <div className="text-[9px] font-bold text-white/20 uppercase tracking-widest">
           Total Records: {filteredViolations.length}
         </div>
         <div className="text-[9px] font-bold text-white/20 uppercase tracking-widest">
           SentinelCam Database Engine v1.0
         </div>
      </div>
    </div>
  );
}
