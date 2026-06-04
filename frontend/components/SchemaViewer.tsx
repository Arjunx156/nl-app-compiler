"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Download, Database, LayoutTemplate, Network, ShieldCheck, Code, CheckCircle, AlertTriangle, Info } from "lucide-react";
import type { CompilationResult } from "@/lib/types";
import { cn } from "@/lib/utils";

interface SchemaViewerProps {
  result: CompilationResult;
}

export function SchemaViewer({ result }: SchemaViewerProps) {
  const [activeTab, setActiveTab] = useState<"ui" | "api" | "db" | "auth" | "intent" | "json">("db");
  const [copied, setCopied] = useState(false);

  if (result.clarification_needed) {
    return (
      <div className="w-full max-w-4xl mx-auto mt-8 glass-panel border-amber-500/30 overflow-hidden">
        <div className="p-6 bg-amber-500/10 flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-amber-500 mt-1 flex-shrink-0" />
          <div>
            <h3 className="text-lg font-medium text-amber-400">Clarification Needed</h3>
            <p className="text-slate-300 mt-2">{result.clarification_needed.reason}</p>
            <div className="mt-4 space-y-2">
              {result.clarification_needed.questions.map((q, i) => (
                <div key={i} className="flex gap-2 items-start bg-black/20 p-3 rounded-lg border border-amber-500/20">
                  <span className="text-amber-500 font-bold">{i + 1}.</span>
                  <span className="text-slate-200">{q}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `schema_${result.generation_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyToClipboard = () => {
    let content = "";
    if (activeTab === "json") content = JSON.stringify(result, null, 2);
    else content = JSON.stringify(result.schemas[activeTab as keyof typeof result.schemas], null, 2);
    
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    { id: "db", label: "Database", icon: Database, data: result.schemas.db },
    { id: "api", label: "API Routes", icon: Network, data: result.schemas.api },
    { id: "ui", label: "UI / Pages", icon: LayoutTemplate, data: result.schemas.ui },
    { id: "auth", label: "Auth / Roles", icon: ShieldCheck, data: result.schemas.auth },
    { id: "intent", label: "Extracted Intent", icon: Info, data: result.intent },
    { id: "json", label: "Full Output", icon: Code, data: result },
  ] as const;

  const currentData = tabs.find(t => t.id === activeTab)?.data;

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-6xl mx-auto mt-8 glass-panel overflow-hidden flex flex-col h-[800px]"
    >
      {/* Header */}
      <div className="p-6 border-b border-slate-700/50 bg-slate-800/50 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <SparklesIcon className="w-5 h-5 text-indigo-400" />
            {result.intent?.app_name || "Generated Schema"}
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full border",
              result.status === "success" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
              "bg-amber-500/10 text-amber-400 border-amber-500/20"
            )}>
              {result.status.toUpperCase()}
            </span>
          </h2>
          <p className="text-sm text-slate-400 mt-1 flex gap-4">
            <span>{result.execution_preview.table_count} Tables</span>
            <span>{result.execution_preview.endpoint_count} Endpoints</span>
            <span>{result.execution_preview.page_count} Pages</span>
            <span>${result.metadata.cost_usd.toFixed(4)}</span>
          </p>
        </div>

        <button
          onClick={handleDownload}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-lg transition-colors text-sm font-medium"
        >
          <Download className="w-4 h-4" />
          Download JSON
        </button>
      </div>

      {/* Tabs */}
      <div className="flex overflow-x-auto border-b border-slate-700/50 bg-slate-900/50 no-scrollbar">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                "flex items-center gap-2 px-6 py-4 text-sm font-medium transition-colors relative whitespace-nowrap",
                isActive ? "text-indigo-400" : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              )}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
              {isActive && (
                <motion.div 
                  layoutId="activeTab" 
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500" 
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <div className="flex-1 relative bg-[#1e1e1e] overflow-hidden group">
        <button 
          onClick={copyToClipboard}
          className="absolute top-4 right-4 z-10 p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-600 opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2 text-xs"
        >
          {copied ? <CheckCircle className="w-3 h-3 text-emerald-400" /> : <Code className="w-3 h-3" />}
          {copied ? "Copied!" : "Copy"}
        </button>
        
        <div className="h-full overflow-auto custom-scrollbar">
          <SyntaxHighlighter
            language="json"
            style={vscDarkPlus}
            customStyle={{ margin: 0, padding: '1.5rem', background: 'transparent', fontSize: '13px' }}
            showLineNumbers={true}
          >
            {JSON.stringify(currentData, null, 2)}
          </SyntaxHighlighter>
        </div>
      </div>
      
      {/* Validation Report Footer */}
      {result.validation_report.unfixed_errors.length > 0 && (
        <div className="p-4 bg-amber-950/30 border-t border-amber-900/50">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
            <div>
              <p className="text-sm text-amber-400 font-medium">
                {result.validation_report.unfixed_errors.length} validation errors remaining after {result.validation_report.repair_iterations} repair attempts.
              </p>
              <p className="text-xs text-amber-500/70 mt-1">Check the full JSON output for error details.</p>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
}

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z" />
    </svg>
  );
}
