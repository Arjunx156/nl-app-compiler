"use client";

import type { AuthSchema } from "@/lib/types";
import { Check, ShieldAlert } from "lucide-react";

export function PermissionsMatrix({ schema }: { schema: AuthSchema | null }) {
  if (!schema || !schema.permission_matrix) return <div className="text-[#737373]">No auth schema available.</div>;

  // Extract all unique resources
  const resources = new Set<string>();
  schema.permission_matrix.roles.forEach(role => {
    role.permissions.forEach(p => resources.add(p.resource));
  });
  const resourcesList = Array.from(resources).sort();

  return (
    <div className="bg-[#111111] border border-[#1f1f1f] rounded-lg overflow-hidden">
      <div className="px-6 py-4 border-b border-[#1f1f1f] bg-[#161616] flex justify-between items-center">
        <h3 className="text-sm font-semibold text-[#f5f5f5]">Role Permissions</h3>
        <div className="text-xs text-[#737373] bg-[#0a0a0a] px-2 py-1 rounded border border-[#1f1f1f]">
          Strategy: <span className="text-[#7c3aed]">{schema.strategy}</span>
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-xs text-left">
          <thead className="text-[#737373] uppercase bg-[#0a0a0a] border-b border-[#1f1f1f]">
            <tr>
              <th className="px-6 py-4 font-semibold">Resource</th>
              {schema.roles.map(role => (
                <th key={role} className="px-6 py-4 font-semibold text-center">{role}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1f1f1f]">
            {resourcesList.map(res => (
              <tr key={res} className="hover:bg-[#161616] transition-colors">
                <td className="px-6 py-4 font-mono font-medium text-[#a3a3a3]">{res}</td>
                {schema.roles.map(role => {
                  const roleDef = schema.permission_matrix.roles.find(r => r.role === role);
                  const perm = roleDef?.permissions.find(p => p.resource === res);
                  const actions = perm ? perm.actions : [];
                  
                  return (
                    <td key={role} className="px-6 py-4 text-center">
                      {actions.length > 0 ? (
                        <div className="flex flex-wrap justify-center gap-1">
                          {actions.map(a => (
                            <span key={a} className={`px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wide border
                              ${a === 'create' ? 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20' : 
                                a === 'read' ? 'text-blue-400 bg-blue-400/10 border-blue-400/20' : 
                                a === 'update' ? 'text-amber-400 bg-amber-400/10 border-amber-400/20' : 
                                'text-red-400 bg-red-400/10 border-red-400/20'}`}
                            >
                              {a}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-[#333]">-</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
