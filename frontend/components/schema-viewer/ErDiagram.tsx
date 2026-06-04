"use client";

import { Key, Link as LinkIcon } from "lucide-react";
import type { DBSchema, TableSpec } from "@/lib/types";

export function ErDiagram({ schema }: { schema: DBSchema | null }) {
  if (!schema || !schema.tables) return <div className="text-[#737373]">No database schema available.</div>;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {schema.tables.map((table: TableSpec) => (
        <div key={table.name} className="bg-[#111111] border border-[#1f1f1f] rounded-xl overflow-hidden shadow-xl">
          <div className="bg-[#161616] px-4 py-3 border-b border-[#1f1f1f] flex justify-between items-center">
            <h3 className="font-mono text-sm font-bold text-[#f5f5f5]">{table.name}</h3>
            <span className="text-[10px] uppercase text-[#737373] bg-[#0a0a0a] px-2 py-0.5 rounded border border-[#1f1f1f]">
              {table.columns.length} cols
            </span>
          </div>
          <div className="p-0">
            <table className="w-full text-xs font-mono text-left border-collapse">
              <tbody>
                {table.columns.map((col, idx) => (
                  <tr key={col.name} className="border-b border-[#1f1f1f]/50 last:border-0 hover:bg-[#1a1a1a]">
                    <td className="px-4 py-2 text-[#f5f5f5] flex items-center gap-2">
                      {col.is_pk ? <Key className="w-3 h-3 text-[#f59e0b]" /> : col.is_fk ? <LinkIcon className="w-3 h-3 text-[#7c3aed]" /> : <div className="w-3" />}
                      {col.name}
                    </td>
                    <td className="px-4 py-2 text-[#7c3aed]">{col.type}</td>
                    <td className="px-4 py-2 text-[#737373]">
                      {!col.nullable && "NN "}
                      {col.unique && "UQ"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
