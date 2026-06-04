"use client";

import type { UISchema, PageUISpec } from "@/lib/types";
import { FolderTree, File as FileIcon, Lock } from "lucide-react";

export function SiteMapTree({ schema }: { schema: UISchema | null }) {
  if (!schema || !schema.pages) return <div className="text-[#737373]">No UI schema available.</div>;

  return (
    <div className="bg-[#111111] border border-[#1f1f1f] rounded-lg p-6">
      <h3 className="text-sm font-semibold text-[#f5f5f5] flex items-center gap-2 mb-6">
        <FolderTree className="w-4 h-4 text-[#7c3aed]" />
        Application Structure
      </h3>
      
      <div className="space-y-2 font-mono text-sm">
        {schema.pages.map((page: PageUISpec) => (
          <div key={page.route} className="flex flex-col border-l-2 border-[#1f1f1f] ml-2 pl-4 py-2 relative group">
            <div className="absolute w-4 h-0.5 bg-[#1f1f1f] left-0 top-5 -ml-4"></div>
            
            <div className="flex items-center justify-between bg-[#161616] p-3 rounded border border-[#1f1f1f]/50 group-hover:border-[#7c3aed]/30 transition-colors">
              <div className="flex items-center gap-3 text-[#f5f5f5]">
                <FileIcon className="w-4 h-4 text-[#737373]" />
                <span className="font-medium">{page.title}</span>
                <span className="text-xs text-[#737373] bg-[#0a0a0a] px-2 py-0.5 rounded">{page.route}</span>
              </div>
              
              <div className="flex items-center gap-3">
                {page.requires_auth && (
                  <div className="flex items-center gap-1 text-xs text-[#f59e0b]">
                    <Lock className="w-3 h-3" />
                    <span>{page.roles_allowed?.join(", ")}</span>
                  </div>
                )}
                <span className="text-[10px] uppercase tracking-wider text-[#7c3aed] bg-[#7c3aed]/10 px-2 py-1 rounded">
                  {page.layout} Layout
                </span>
              </div>
            </div>
            
            {page.components && page.components.length > 0 && (
              <div className="mt-2 ml-6 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
                {page.components.map((comp, idx) => (
                  <div key={idx} className="bg-[#0a0a0a] border border-[#1f1f1f] p-2 rounded text-xs flex flex-col gap-1">
                    <span className="text-[#a3a3a3] font-semibold">{comp.type}</span>
                    {comp.data_binding && (
                      <span className="text-[10px] text-[#10b981] truncate border border-[#10b981]/20 bg-[#10b981]/5 px-1 py-0.5 rounded">
                        API: {comp.data_binding}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
