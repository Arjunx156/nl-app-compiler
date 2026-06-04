"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PipelineEvent } from "@/lib/types";

interface PipelineStatusProps {
  events: PipelineEvent[];
  isComplete: boolean;
}

const STAGES = [
  { id: "intent", label: "Intent Extraction" },
  { id: "architect", label: "System Architecture" },
  { id: "schemas", label: "Schema Generation" },
  { id: "validation", label: "Cross-Layer Validation" },
  { id: "repair", label: "Self-Healing & Repair" },
];

export function PipelineStatus({ events, isComplete }: PipelineStatusProps) {
  if (events.length === 0 && !isComplete) return null;

  // Compute status for each stage
  const getStageStatus = (stageId: string) => {
    // If we have an error anywhere, and this stage hasn't started, it's skipped
    const hasError = events.some(e => e.status === "error");
    
    // Find the latest event for this stage
    const stageEvents = events.filter(e => e.stage === stageId);
    if (stageEvents.length === 0) return hasError ? "skipped" : "pending";
    
    const latest = stageEvents[stageEvents.length - 1];
    return latest.status || "pending";
  };

  const getStageMessage = (stageId: string) => {
    const stageEvents = events.filter(e => e.stage === stageId);
    if (stageEvents.length === 0) return "";
    return stageEvents[stageEvents.length - 1].message || "";
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="w-full max-w-4xl mx-auto mt-8 glass-panel overflow-hidden"
    >
      <div className="p-6 border-b border-slate-700/50 bg-slate-800/30 flex justify-between items-center">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            {!isComplete && <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
            </span>}
            Pipeline Status
          </h2>
          <p className="text-xs text-slate-400 mt-1">Real-time compilation progress</p>
        </div>
        
        {/* Token/Latency tracker could go here */}
        <div className="text-right">
          {events.length > 0 && (
            <div className="text-xs font-mono text-slate-400 flex flex-col gap-1">
              <span>{events[events.length - 1].elapsed_ms || 0} ms</span>
              <span className="text-indigo-400">{events[events.length - 1].tokens_used || 0} tokens</span>
            </div>
          )}
        </div>
      </div>

      <div className="p-6">
        <div className="space-y-6">
          {STAGES.map((stage, idx) => {
            const status = getStageStatus(stage.id);
            const msg = getStageMessage(stage.id);
            const isLast = idx === STAGES.length - 1;
            
            // Skip repair stage visually if not needed (only if pipeline complete and no repair events)
            if (stage.id === "repair" && isComplete && status === "pending") return null;

            return (
              <div key={stage.id} className="relative">
                {/* Connecting line */}
                {!isLast && (
                  <div className={cn(
                    "absolute left-3.5 top-8 w-px h-full -ml-px",
                    status === "done" ? "bg-indigo-500" : "bg-slate-700"
                  )} />
                )}
                
                <div className="relative flex items-start gap-4">
                  <div className={cn(
                    "flex items-center justify-center w-7 h-7 rounded-full mt-0.5 z-10 bg-slate-900 border",
                    status === "done" ? "border-indigo-500 text-indigo-400" :
                    status === "running" ? "border-cyan-500 text-cyan-400" :
                    status === "error" ? "border-red-500 text-red-400" :
                    "border-slate-700 text-slate-600"
                  )}>
                    {status === "done" ? <CheckCircle2 className="w-4 h-4" /> :
                     status === "running" ? <Loader2 className="w-4 h-4 animate-spin" /> :
                     status === "error" ? <XCircle className="w-4 h-4" /> :
                     <Circle className="w-4 h-4" />}
                  </div>
                  
                  <div className="flex-1 pb-2">
                    <h3 className={cn(
                      "font-medium",
                      status === "done" ? "text-indigo-300" :
                      status === "running" ? "text-cyan-300" :
                      status === "error" ? "text-red-400" :
                      "text-slate-500"
                    )}>
                      {stage.label}
                    </h3>
                    
                    {msg && (
                      <motion.div 
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className={cn(
                          "mt-1 text-sm font-mono p-2 rounded bg-slate-900/50 border",
                          status === "error" ? "border-red-900/50 text-red-300" : "border-slate-700/50 text-slate-400"
                        )}
                      >
                        {msg}
                      </motion.div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      
      {/* Live Log Stream */}
      <div className="bg-black/40 p-4 font-mono text-[11px] leading-relaxed max-h-40 overflow-y-auto border-t border-slate-700/50">
        {events.filter(e => e.type === "log" || e.type === "progress").slice(-5).map((e, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-slate-500">[{new Date(e.timestamp || Date.now()).toISOString().split('T')[1].slice(0,-1)}]</span>
            <span className={cn(
              e.level === "error" ? "text-red-400" : 
              e.level === "warning" ? "text-amber-400" : 
              "text-slate-300"
            )}>
              {e.message}
            </span>
          </div>
        ))}
        {!isComplete && events.length > 0 && (
          <div className="flex gap-2 mt-1 opacity-50">
            <span className="text-slate-500">[{new Date().toISOString().split('T')[1].slice(0,-1)}]</span>
            <span className="text-slate-400 animate-pulse">_</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
