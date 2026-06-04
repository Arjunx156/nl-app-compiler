"use client";

import type { APISchema, EndpointSpec } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Lock, Unlock } from "lucide-react";

export function ApiEndpointList({ schema }: { schema: APISchema | null }) {
  if (!schema || !schema.endpoints) return <div className="text-[#737373]">No API schema available.</div>;

  const methodColors: Record<string, string> = {
    GET: "text-[#10b981] bg-[#10b981]/10 border-[#10b981]/20",
    POST: "text-[#3b82f6] bg-[#3b82f6]/10 border-[#3b82f6]/20",
    PUT: "text-[#f59e0b] bg-[#f59e0b]/10 border-[#f59e0b]/20",
    PATCH: "text-[#f59e0b] bg-[#f59e0b]/10 border-[#f59e0b]/20",
    DELETE: "text-[#ef4444] bg-[#ef4444]/10 border-[#ef4444]/20",
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-[#737373] mb-6 font-mono">
        Base URL: <span className="text-[#f5f5f5]">{schema.base_url}</span> ({schema.version})
      </div>
      
      {schema.endpoints.map((ep: EndpointSpec) => (
        <div key={ep.id} className="bg-[#111111] border border-[#1f1f1f] rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-[#1f1f1f] flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#161616]">
            <div className="flex items-center gap-4">
              <span className={cn("px-2.5 py-1 text-xs font-bold rounded border w-16 text-center", methodColors[ep.method] || "text-gray-400")}>
                {ep.method}
              </span>
              <span className="font-mono text-sm font-medium text-[#f5f5f5]">{ep.path}</span>
            </div>
            <div className="flex items-center gap-3">
              {ep.auth_required ? (
                <div className="flex items-center gap-1 text-xs text-[#f59e0b] bg-[#f59e0b]/10 px-2 py-1 rounded border border-[#f59e0b]/20">
                  <Lock className="w-3 h-3" /> Auth Required
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-[#10b981] bg-[#10b981]/10 px-2 py-1 rounded border border-[#10b981]/20">
                  <Unlock className="w-3 h-3" /> Public
                </div>
              )}
            </div>
          </div>
          
          <div className="p-4 space-y-4">
            <p className="text-sm text-[#a3a3a3]">{ep.summary}</p>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Request */}
              <div className="bg-[#0a0a0a] border border-[#1f1f1f] rounded-lg p-3">
                <h4 className="text-xs font-semibold text-[#737373] uppercase mb-2">Request Body</h4>
                {ep.request_body ? (
                  <pre className="text-[11px] font-mono text-[#a3a3a3] overflow-x-auto">
                    {JSON.stringify(ep.request_body.example, null, 2)}
                  </pre>
                ) : (
                  <span className="text-xs text-[#525252] italic">No request body</span>
                )}
              </div>
              
              {/* Response */}
              <div className="bg-[#0a0a0a] border border-[#1f1f1f] rounded-lg p-3">
                <h4 className="text-xs font-semibold text-[#737373] uppercase mb-2">Response ({ep.response.status_code})</h4>
                <pre className="text-[11px] font-mono text-[#a3a3a3] overflow-x-auto">
                  {JSON.stringify(ep.response.example, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
