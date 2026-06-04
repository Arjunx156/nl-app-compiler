"use client";

import { useState } from "react";
import { PromptInput } from "@/components/PromptInput";
import { PipelineStatus } from "@/components/PipelineStatus";
import { SchemaViewer } from "@/components/SchemaViewer";
import { generateApp } from "@/lib/api";
import type { PipelineEvent, CompilationResult } from "@/lib/types";

export default function Home() {
  const [isLoading, setIsLoading] = useState(false);
  const [events, setEvents] = useState<PipelineEvent[]>([]);
  const [result, setResult] = useState<CompilationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = (prompt: string) => {
    setIsLoading(true);
    setEvents([]);
    setResult(null);
    setError(null);

    generateApp(
      prompt,
      (event) => setEvents((prev) => [...prev, event]),
      (finalResult) => {
        setResult(finalResult);
        setIsLoading(false);
      },
      (errMsg) => {
        setError(errMsg);
        setIsLoading(false);
      }
    );
  };

  return (
    <main className="min-h-screen py-16 px-4 sm:px-6 relative flex flex-col items-center">
      {/* Background decorations */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-[500px] opacity-20 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] rounded-full bg-indigo-500 mix-blend-screen filter blur-[100px] animate-blob" />
        <div className="absolute top-[10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-cyan-500 mix-blend-screen filter blur-[100px] animate-blob animation-delay-2000" />
      </div>

      <div className="w-full max-w-7xl mx-auto z-10 space-y-12">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-1.5 mb-4 rounded-full bg-slate-800/50 border border-slate-700/50 backdrop-blur-sm">
            <span className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-indigo-400">
              Agentic Coding Phase 1
            </span>
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight text-white drop-shadow-sm">
            NL to App <span className="text-gradient">Compiler</span>
          </h1>
          <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto">
            Describe your application in natural language. Watch the AI architect the database, API, UI, and auth schemas in real-time.
          </p>
        </div>

        {/* Main Input Area */}
        <div className="mt-12">
          <PromptInput onSubmit={handleGenerate} isLoading={isLoading} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="w-full max-w-4xl mx-auto mt-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-center">
            {error}
          </div>
        )}

        {/* Live Status Tracker */}
        {(isLoading || (events.length > 0 && !result)) && (
          <PipelineStatus events={events} isComplete={!!result} />
        )}

        {/* Final Output */}
        {result && (
          <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
            <SchemaViewer result={result} />
          </div>
        )}
      </div>
    </main>
  );
}
