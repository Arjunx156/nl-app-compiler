"use client";

import { useState, useEffect } from "react";
import { getEvalResults, runAllEvaluations, runSingleEval } from "@/lib/api";
import type { EvalResult, EvalAggregate } from "@/lib/types";
import { Play, Activity, Target, Zap, Wrench } from "lucide-react";
import { cn } from "@/lib/utils";

export default function EvalPage() {
  const [results, setResults] = useState<EvalResult[]>([]);
  const [aggregate, setAggregate] = useState<EvalAggregate | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [currentTest, setCurrentTest] = useState<string | null>(null);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = () => {
    getEvalResults().then(data => {
      setResults(data);
      setLoading(false);
      // Mock aggregate computation if not provided directly
      if (data.length > 0) {
        const successes = data.filter(d => d.score === 100).length;
        setAggregate({
          total: data.length,
          success_rate: (successes / data.length) * 100,
          avg_latency_ms: data.reduce((acc, d) => acc + d.latency_ms, 0) / data.length,
          avg_cost_usd: data.reduce((acc, d) => acc + d.cost_usd, 0) / data.length,
          avg_score: data.reduce((acc, d) => acc + d.score, 0) / data.length,
          avg_repair_iterations: data.reduce((acc, d) => acc + d.repair_iterations, 0) / data.length,
          results: data
        });
      }
    });
  };

  const handleRunAll = () => {
    setRunning(true);
    runAllEvaluations(
      (event: any) => setCurrentTest(event.test_id),
      (aggr) => {
        setAggregate(aggr);
        setResults(aggr.results);
        setRunning(false);
        setCurrentTest(null);
      },
      (err) => {
        console.error(err);
        setRunning(false);
      }
    );
  };

  const normalTests = results.filter(r => r.category === "normal");
  const edgeTests = results.filter(r => r.category === "edge");

  return (
    <div className="min-h-screen bg-[#0a0a0a] pt-24 px-6 pb-12">
      <div className="max-w-6xl mx-auto space-y-8">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <h1 className="text-3xl font-bold text-[#f5f5f5]">Evaluation Dashboard</h1>
            <p className="text-[#737373] mt-2">Automated testing of the Compiler against 20 hardcoded test cases.</p>
          </div>
          
          <button 
            onClick={handleRunAll}
            disabled={running || loading}
            className={cn(
              "flex items-center gap-2 px-6 py-2.5 rounded-lg font-medium transition-colors",
              running ? "bg-[#333] text-[#737373] cursor-not-allowed" : "bg-[#7c3aed] hover:bg-[#6d28d9] text-white"
            )}
          >
            {running ? <Activity className="w-4 h-4 animate-pulse" /> : <Play className="w-4 h-4" />}
            {running ? "Running Evaluations..." : "Run All Evaluations"}
          </button>
        </div>

        {/* Metrics Overview */}
        {aggregate && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard icon={Target} title="Success Rate" value={`${aggregate.success_rate.toFixed(1)}%`} color="text-[#10b981]" />
            <MetricCard icon={Zap} title="Avg Latency" value={`${(aggregate.avg_latency_ms / 1000).toFixed(2)}s`} color="text-[#f5f5f5]" />
            <MetricCard icon={Activity} title="Avg Cost" value={`$${aggregate.avg_cost_usd.toFixed(4)}`} color="text-[#7c3aed]" />
            <MetricCard icon={Wrench} title="Avg Repairs" value={aggregate.avg_repair_iterations.toFixed(1)} color="text-[#f59e0b]" />
          </div>
        )}

        <div className="space-y-8">
          <TestTable title="Normal Cases" description="Standard application requirements." tests={normalTests} currentTest={currentTest} />
          <TestTable title="Edge Cases" description="Vague, contradictory, or complex prompts." tests={edgeTests} currentTest={currentTest} />
        </div>
      </div>
    </div>
  );
}

function MetricCard({ icon: Icon, title, value, color }: any) {
  return (
    <div className="bg-[#111111] border border-[#1f1f1f] rounded-xl p-5 flex flex-col gap-2 shadow-lg">
      <div className="flex items-center gap-2 text-[#737373] text-sm font-medium">
        <Icon className="w-4 h-4" /> {title}
      </div>
      <div className={cn("text-3xl font-bold font-mono", color)}>{value}</div>
    </div>
  );
}

function TestTable({ title, description, tests, currentTest }: any) {
  if (tests.length === 0) return null;
  
  return (
    <div className="bg-[#111111] border border-[#1f1f1f] rounded-xl overflow-hidden shadow-2xl">
      <div className="px-6 py-4 border-b border-[#1f1f1f] bg-[#161616]">
        <h2 className="text-lg font-semibold text-[#f5f5f5]">{title}</h2>
        <p className="text-sm text-[#737373]">{description}</p>
      </div>
      <table className="w-full text-sm text-left">
        <thead className="text-[#737373] uppercase text-xs border-b border-[#1f1f1f]">
          <tr>
            <th className="px-6 py-3">ID / Name</th>
            <th className="px-6 py-3">Status</th>
            <th className="px-6 py-3 text-center">Score</th>
            <th className="px-6 py-3 text-center">Repairs</th>
            <th className="px-6 py-3 text-right">Metrics</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#1f1f1f]">
          {tests.map((test: EvalResult) => (
            <tr key={test.id} className={cn("transition-colors", currentTest === test.test_id ? "bg-[#7c3aed]/10" : "hover:bg-[#1a1a1a]")}>
              <td className="px-6 py-4">
                <div className="flex flex-col gap-1">
                  <span className="text-[#f5f5f5] font-medium">{test.test_name}</span>
                  <span className="text-xs font-mono text-[#737373]">{test.test_id}</span>
                </div>
              </td>
              <td className="px-6 py-4">
                {currentTest === test.test_id ? (
                  <span className="text-cyan-400 flex items-center gap-2 text-xs font-medium bg-cyan-400/10 px-2.5 py-1 border border-cyan-400/20 rounded max-w-fit">
                    <Activity className="w-3 h-3 animate-pulse" /> RUNNING
                  </span>
                ) : (
                  <span className={cn(
                    "px-2.5 py-1 text-xs rounded border uppercase font-medium tracking-wide",
                    test.status === "passed" ? "bg-[#10b981]/10 text-[#10b981] border-[#10b981]/20" :
                    test.status === "failed" ? "bg-[#ef4444]/10 text-[#ef4444] border-[#ef4444]/20" :
                    "bg-[#333] text-[#a3a3a3] border-[#444]"
                  )}>
                    {test.status}
                  </span>
                )}
              </td>
              <td className="px-6 py-4 text-center">
                <span className={cn("font-bold font-mono", test.score === 100 ? "text-[#10b981]" : test.score >= 50 ? "text-[#f59e0b]" : "text-[#ef4444]")}>
                  {test.score}%
                </span>
              </td>
              <td className="px-6 py-4 text-center">
                <span className="text-[#f5f5f5]">{test.repair_iterations}</span>
              </td>
              <td className="px-6 py-4 text-right">
                <div className="flex flex-col gap-1 text-xs">
                  <span className="text-[#7c3aed] font-mono">${test.cost_usd.toFixed(4)}</span>
                  <span className="text-[#737373]">{test.latency_ms} ms</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
