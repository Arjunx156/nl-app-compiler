"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { listGenerations } from "@/lib/api";
import type { GenerationSummary } from "@/lib/types";
import { Search, ChevronRight, Clock, Database, LayoutTemplate, Network } from "lucide-react";
import { cn } from "@/lib/utils";

export default function HistoryPage() {
  const router = useRouter();
  const [generations, setGenerations] = useState<GenerationSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchGenerations();
  }, []);

  const fetchGenerations = (q?: string) => {
    setLoading(true);
    listGenerations(q).then(data => {
      setGenerations(data);
      setLoading(false);
    }).catch(() => setLoading(false));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchGenerations(search);
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] pt-24 px-6 pb-12">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <h1 className="text-3xl font-bold text-[#f5f5f5]">Generation History</h1>
            <p className="text-[#737373] mt-2">View and manage all previously compiled applications.</p>
          </div>
          
          <form onSubmit={handleSearch} className="relative w-full sm:w-72">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#737373]" />
            <input 
              type="text" 
              placeholder="Search prompts..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#111111] border border-[#1f1f1f] rounded-lg pl-9 pr-4 py-2 text-sm text-[#f5f5f5] placeholder:text-[#525252] focus:outline-none focus:border-[#7c3aed]"
            />
          </form>
        </div>

        {loading ? (
          <div className="text-center py-20 text-[#737373] animate-pulse">Loading history...</div>
        ) : generations.length === 0 ? (
          <div className="text-center py-20 bg-[#111111] border border-[#1f1f1f] rounded-xl text-[#737373]">
            No generations found.
          </div>
        ) : (
          <div className="bg-[#111111] border border-[#1f1f1f] rounded-xl overflow-hidden shadow-2xl">
            <table className="w-full text-sm text-left">
              <thead className="text-[#737373] uppercase text-xs bg-[#161616] border-b border-[#1f1f1f]">
                <tr>
                  <th className="px-6 py-4 font-semibold">Prompt / App Type</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold text-center">Size</th>
                  <th className="px-6 py-4 font-semibold text-right">Metrics</th>
                  <th className="px-6 py-4 font-semibold"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1f1f1f]">
                {generations.map((gen) => (
                  <tr 
                    key={gen.id} 
                    onClick={() => router.push(`/result/${gen.id}`)}
                    className="hover:bg-[#1a1a1a] transition-colors cursor-pointer group"
                  >
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1">
                        <span className="text-[#f5f5f5] font-medium line-clamp-1">{gen.prompt_preview}</span>
                        <div className="flex items-center gap-2 text-xs">
                          <span className="bg-[#1f1f1f] text-[#a3a3a3] px-2 py-0.5 rounded capitalize">{gen.app_type}</span>
                          <span className="text-[#525252] flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {new Date(gen.created_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        "px-2.5 py-1 text-xs rounded border uppercase font-medium tracking-wide",
                        gen.status === "success" ? "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20" :
                        gen.status === "partial" ? "bg-[#f59e0b]/10 text-[#f59e0b] border-[#f59e0b]/20" :
                        "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20"
                      )}>
                        {gen.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex justify-center gap-4 text-xs text-[#a3a3a3]">
                        <span className="flex items-center gap-1" title="Pages"><LayoutTemplate className="w-3.5 h-3.5" /> {gen.page_count}</span>
                        <span className="flex items-center gap-1" title="API Endpoints"><Network className="w-3.5 h-3.5" /> {gen.endpoint_count}</span>
                        <span className="flex items-center gap-1" title="DB Tables"><Database className="w-3.5 h-3.5" /> {gen.table_count}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex flex-col gap-1 text-xs">
                        <span className="text-[#7c3aed] font-mono">${gen.cost_usd.toFixed(4)}</span>
                        <span className="text-[#737373]">{gen.latency_ms} ms</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <ChevronRight className="w-5 h-5 text-[#333] group-hover:text-[#f5f5f5] transition-colors ml-auto" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
