"use client";

import type { GenerationMetadata } from "@/lib/types";

export function CostBreakdown({ metadata }: { metadata: GenerationMetadata }) {
  if (!metadata || !metadata.model_usage) return <div className="text-[#737373]">No metrics available.</div>;

  const stages = Object.keys(metadata.model_usage);
  
  return (
    <div className="space-y-6 max-w-4xl">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">Total Cost</div>
          <div className="text-2xl font-bold text-[#7c3aed]">${metadata.cost_usd.toFixed(5)}</div>
        </div>
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">Total Tokens</div>
          <div className="text-2xl font-bold text-[#f5f5f5]">{metadata.total_tokens.toLocaleString()}</div>
        </div>
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">LLM Calls</div>
          <div className="text-2xl font-bold text-[#f5f5f5]">{metadata.llm_calls}</div>
        </div>
      </div>

      <div className="bg-[#111111] border border-[#1f1f1f] rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-[#1f1f1f] bg-[#161616]">
          <h3 className="text-sm font-semibold text-[#f5f5f5]">Cost by Stage</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="text-[#737373] uppercase bg-[#0a0a0a] border-b border-[#1f1f1f]">
              <tr>
                <th className="px-6 py-4 font-semibold">Stage</th>
                <th className="px-6 py-4 font-semibold">Model</th>
                <th className="px-6 py-4 font-semibold text-right">Tokens</th>
                <th className="px-6 py-4 font-semibold text-right">Latency</th>
                <th className="px-6 py-4 font-semibold text-right">Cost (USD)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f1f1f]">
              {stages.map(stage => {
                const usage = metadata.model_usage[stage];
                return (
                  <tr key={stage} className="hover:bg-[#161616] transition-colors">
                    <td className="px-6 py-4 font-medium text-[#f5f5f5] capitalize">{stage}</td>
                    <td className="px-6 py-4 font-mono text-[#a3a3a3]">{usage.model}</td>
                    <td className="px-6 py-4 text-right text-[#a3a3a3]">{usage.tokens.toLocaleString()}</td>
                    <td className="px-6 py-4 text-right text-[#a3a3a3]">{usage.latency_ms} ms</td>
                    <td className="px-6 py-4 text-right font-mono text-[#7c3aed]">${usage.cost_usd.toFixed(5)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot className="bg-[#161616] border-t border-[#1f1f1f]">
              <tr>
                <td colSpan={2} className="px-6 py-3 font-semibold text-[#f5f5f5]">Total</td>
                <td className="px-6 py-3 text-right font-semibold text-[#f5f5f5]">{metadata.total_tokens.toLocaleString()}</td>
                <td className="px-6 py-3 text-right font-semibold text-[#f5f5f5]">{metadata.latency_ms} ms</td>
                <td className="px-6 py-3 text-right font-semibold text-[#7c3aed]">${metadata.cost_usd.toFixed(5)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
