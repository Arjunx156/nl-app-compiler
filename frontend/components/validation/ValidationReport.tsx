"use client";

import type { ValidationReport as ReportType } from "@/lib/types";
import { CheckCircle2, XCircle, AlertTriangle, ArrowRight } from "lucide-react";

export function ValidationReport({ report }: { report: ReportType }) {
  if (!report) return null;

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">Checks Run</div>
          <div className="text-2xl font-bold text-[#f5f5f5]">{report.checks_run}</div>
        </div>
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">Passed</div>
          <div className="text-2xl font-bold text-[#10b981]">{report.checks_passed}</div>
        </div>
        <div className="bg-[#111111] p-4 rounded-lg border border-[#1f1f1f]">
          <div className="text-xs text-[#737373] uppercase mb-1">Errors Fixed (AI)</div>
          <div className="text-2xl font-bold text-[#7c3aed]">{report.errors_fixed}</div>
        </div>
        <div className="bg-[#111111] p-4 rounded-lg border border-[#ef4444]/30">
          <div className="text-xs text-[#ef4444] uppercase mb-1">Unfixed Errors</div>
          <div className="text-2xl font-bold text-[#ef4444]">{report.unfixed_errors?.length || 0}</div>
        </div>
      </div>

      {/* Check Results */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-[#f5f5f5] mb-4">Detailed Results</h3>
        {report.check_results.map((check) => (
          <div key={check.check_id} className="bg-[#111111] border border-[#1f1f1f] rounded-lg p-4 flex flex-col sm:flex-row gap-4 justify-between items-start">
            <div className="flex gap-3">
              <div className="mt-0.5">
                {check.passed ? (
                  <CheckCircle2 className="w-5 h-5 text-[#10b981]" />
                ) : (
                  <XCircle className="w-5 h-5 text-[#ef4444]" />
                )}
              </div>
              <div>
                <div className="font-medium text-[#f5f5f5] text-sm flex items-center gap-2">
                  {check.name}
                  <span className="text-[10px] font-mono text-[#737373] bg-[#0a0a0a] px-1.5 py-0.5 rounded border border-[#1f1f1f]">{check.check_id}</span>
                </div>
                <div className="text-xs text-[#a3a3a3] mt-1">{check.description}</div>
                
                {/* Errors list for this check */}
                {!check.passed && check.errors.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {check.errors.map((err, i) => (
                      <div key={i} className="bg-[#ef4444]/5 border border-[#ef4444]/20 p-3 rounded text-xs space-y-2">
                        <div className="flex items-start gap-2 text-[#ef4444]">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                          <span className="font-medium">{err.description}</span>
                        </div>
                        <div className="font-mono text-[#a3a3a3] pl-6">
                          Layer: <span className="text-[#f5f5f5]">{err.layer}</span> | 
                          Stage: <span className="text-[#f5f5f5]">{err.stage}</span>
                        </div>
                        {err.suggested_fix && (
                          <div className="flex items-center gap-2 pl-6 text-[#7c3aed] mt-1">
                            <ArrowRight className="w-3 h-3" />
                            <span>Fix: {err.suggested_fix}</span>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
