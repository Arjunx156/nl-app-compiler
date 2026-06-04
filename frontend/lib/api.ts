/**
 * API client functions for all backend endpoints.
 */

import type {
  CompilationResult,
  GenerationSummary,
  EvalResult,
  EvalAggregate,
  PipelineEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── SSE Generation ────────────────────────────────────────────────────────

export function generateApp(
  prompt: string,
  onEvent: (event: PipelineEvent) => void,
  onComplete: (result: CompilationResult) => void,
  onError: (error: string) => void
): () => void {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data:")) {
            try {
              const raw = line.slice(5).trim();
              if (!raw) continue;
              const parsed = JSON.parse(raw) as PipelineEvent;
              if (parsed.type === "complete") {
                onComplete(parsed.data as CompilationResult);
              } else if (parsed.type === "error") {
                onError((parsed.data as { message: string }).message);
              } else {
                onEvent(parsed);
              }
            } catch (_) {}
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(String(err));
    });

  return () => controller.abort();
}

// ── Generations ───────────────────────────────────────────────────────────

export async function getGeneration(id: string): Promise<CompilationResult> {
  const res = await fetch(`${API_BASE}/api/generations/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch generation ${id}`);
  return res.json();
}

export async function listGenerations(
  search?: string
): Promise<GenerationSummary[]> {
  const url = search
    ? `${API_BASE}/api/generations?search=${encodeURIComponent(search)}`
    : `${API_BASE}/api/generations`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to list generations");
  return res.json();
}

export async function downloadGeneration(id: string): Promise<void> {
  const url = `${API_BASE}/api/generations/${id}/download`;
  const a = document.createElement("a");
  a.href = url;
  a.download = `compilation_${id}.json`;
  a.click();
}

// ── Evaluation ────────────────────────────────────────────────────────────

export function runAllEvaluations(
  onEvent: (event: Record<string, unknown>) => void,
  onComplete: (result: EvalAggregate) => void,
  onError: (error: string) => void
): () => void {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/eval/run-all`, {
    method: "POST",
    signal: controller.signal,
  })
    .then(async (res) => {
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("data:")) {
            try {
              const parsed = JSON.parse(line.slice(5).trim());
              if (parsed.type === "complete") {
                onComplete(parsed.data as EvalAggregate);
              } else {
                onEvent(parsed);
              }
            } catch (_) {}
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(String(err));
    });

  return () => controller.abort();
}

export async function runSingleEval(
  testId: string
): Promise<EvalResult> {
  const res = await fetch(`${API_BASE}/api/eval/run/${testId}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Failed to run eval ${testId}`);
  return res.json();
}

export async function getEvalResults(): Promise<EvalResult[]> {
  const res = await fetch(`${API_BASE}/api/eval/results`);
  if (!res.ok) throw new Error("Failed to fetch eval results");
  return res.json();
}
