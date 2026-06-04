"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getGeneration } from "@/lib/api";
import type { CompilationResult } from "@/lib/types";
import { JsonViewer } from "@/components/schema-viewer/JsonViewer";
import { ErDiagram } from "@/components/schema-viewer/ErDiagram";
import { ApiEndpointList } from "@/components/schema-viewer/ApiEndpointList";
import { SiteMapTree } from "@/components/schema-viewer/SiteMapTree";
import { PermissionsMatrix } from "@/components/schema-viewer/PermissionsMatrix";
import { ValidationReport } from "@/components/validation/ValidationReport";
import { CostBreakdown } from "@/components/metrics/CostBreakdown";
import { cn } from "@/lib/utils";
import { ShieldCheck, Database, Network, LayoutTemplate, Code, CheckCircle, AlertTriangle, BarChart, History } from "lucide-react";

export default function ResultPage() {
  const params = useParams();
  const id = params.id as string;
  const [result, setResult] = useState<CompilationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"json" | "visual" | "validation" | "metrics">("visual");
  const [activeSection, setActiveSection] = useState<"db" | "api" | "ui" | "auth">("db");

  useEffect(() => {
    getGeneration(id)
      .then(res => {
        setResult(res);
        setLoading(false);
      })
      .catch(err => {
        setError(String(err));
        setLoading(false);
      });
  }, [id]);

  if (loading) return <div className="flex h-screen items-center justify-center text-indigo-500 animate-pulse">Loading result...</div>;
  if (error || !result) return <div className="p-8 text-red-500">Error: {error || "Not found"}</div>;

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0a]">
      {/* Top Bar */}
      <div className="h-16 border-b border-[#1f1f1f] bg-[#111111] flex items-center justify-between px-6">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-[#f5f5f5] flex items-center gap-2">
            Result <span className="text-[#737373] text-sm font-mono">{id.substring(0,8)}</span>
          </h1>
          <span className={cn(
            "px-2 py-0.5 text-xs rounded border uppercase font-medium tracking-wide",
            result.status === "success" ? "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20" :
            result.status === "partial" ? "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20" :
            "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20"
          )}>
            {result.status}
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm text-[#737373]">
          <span className="flex items-center gap-2"><History className="w-4 h-4" /> {result.metadata.latency_ms} ms</span>
          <span className="flex items-center gap-2"><span className="font-mono text-[#7c3aed]">${result.metadata.cost_usd.toFixed(4)}</span></span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <div className="w-[280px] border-r border-[#1f1f1f] bg-[#111111] overflow-y-auto p-4 flex flex-col gap-2">
          <div className="text-xs font-semibold text-[#737373] uppercase tracking-wider mb-2 mt-4 px-2">Visualizer</div>
          
          <SidebarBtn active={activeTab === "visual" && activeSection === "db"} onClick={() => { setActiveTab("visual"); setActiveSection("db"); }} icon={Database} label="DB Schema" />
          <SidebarBtn active={activeTab === "visual" && activeSection === "api"} onClick={() => { setActiveTab("visual"); setActiveSection("api"); }} icon={Network} label="API Schema" />
          <SidebarBtn active={activeTab === "visual" && activeSection === "ui"} onClick={() => { setActiveTab("visual"); setActiveSection("ui"); }} icon={LayoutTemplate} label="UI Schema" />
          <SidebarBtn active={activeTab === "visual" && activeSection === "auth"} onClick={() => { setActiveTab("visual"); setActiveSection("auth"); }} icon={ShieldCheck} label="Auth Schema" />
          
          <div className="text-xs font-semibold text-[#737373] uppercase tracking-wider mb-2 mt-6 px-2">Reports</div>
          
          <SidebarBtn active={activeTab === "validation"} onClick={() => setActiveTab("validation")} icon={result.validation_report.unfixed_errors.length === 0 ? CheckCircle : AlertTriangle} label="Validation Report" error={result.validation_report.unfixed_errors.length > 0} />
          <SidebarBtn active={activeTab === "metrics"} onClick={() => setActiveTab("metrics")} icon={BarChart} label="Metrics" />
          <SidebarBtn active={activeTab === "json"} onClick={() => setActiveTab("json")} icon={Code} label="Raw JSON" />
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto bg-[#0a0a0a]">
          {activeTab === "visual" && (
            <div className="p-8">
              {activeSection === "db" && <ErDiagram schema={result.schemas.db} />}
              {activeSection === "api" && <ApiEndpointList schema={result.schemas.api} />}
              {activeSection === "ui" && <SiteMapTree schema={result.schemas.ui} />}
              {activeSection === "auth" && <PermissionsMatrix schema={result.schemas.auth} />}
            </div>
          )}
          
          {activeTab === "validation" && (
            <div className="p-8">
              <ValidationReport report={result.validation_report} />
            </div>
          )}

          {activeTab === "metrics" && (
            <div className="p-8">
              <CostBreakdown metadata={result.metadata} />
            </div>
          )}

          {activeTab === "json" && (
            <div className="p-0 h-full">
              <JsonViewer data={result} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SidebarBtn({ active, onClick, icon: Icon, label, error }: any) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors w-full text-left",
        active ? "bg-[rgba(124,58,237,0.15)] text-[#7c3aed]" : "text-[#737373] hover:bg-[#1f1f1f] hover:text-[#f5f5f5]",
        error && !active && "text-[#ef4444]"
      )}
    >
      <Icon className={cn("w-4 h-4", error && "text-[#ef4444]")} />
      {label}
    </button>
  );
}
