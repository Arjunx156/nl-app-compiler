"use client";

import { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Sparkles, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface PromptInputProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

export function PromptInput({ onSubmit, isLoading }: PromptInputProps) {
  const [prompt, setPrompt] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [prompt]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (prompt.trim() && !isLoading) {
      onSubmit(prompt.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-4xl mx-auto"
    >
      <form onSubmit={handleSubmit} className="relative group">
        <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-cyan-500 rounded-2xl blur opacity-25 group-hover:opacity-40 transition duration-1000 group-hover:duration-200"></div>
        <div className="relative flex flex-col bg-slate-900 ring-1 ring-white/10 rounded-2xl overflow-hidden shadow-2xl transition-all">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your app idea in detail... (e.g. 'Build a CRM with role-based access for sales reps and managers')"
            className="w-full bg-transparent text-slate-100 placeholder:text-slate-500 p-6 pb-16 resize-none focus:outline-none min-h-[120px] max-h-[300px]"
            disabled={isLoading}
          />
          
          <div className="absolute bottom-0 left-0 right-0 p-4 flex justify-between items-center bg-gradient-to-t from-slate-900 via-slate-900 to-transparent pt-8">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <kbd className="px-2 py-1 bg-slate-800 rounded border border-slate-700 font-sans">⌘</kbd>
              <span>+</span>
              <kbd className="px-2 py-1 bg-slate-800 rounded border border-slate-700 font-sans">Enter</kbd>
              <span className="ml-2">to generate</span>
            </div>
            
            <button
              type="submit"
              disabled={!prompt.trim() || isLoading}
              className={cn(
                "flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium transition-all duration-300",
                !prompt.trim() || isLoading
                  ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                  : "bg-indigo-500 hover:bg-indigo-400 text-white shadow-[0_0_20px_rgba(99,102,241,0.4)] hover:shadow-[0_0_30px_rgba(99,102,241,0.6)] hover:-translate-y-0.5"
              )}
            >
              {isLoading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Compiling...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Generate Schema</span>
                  <ArrowRight className="w-4 h-4 ml-1" />
                </>
              )}
            </button>
          </div>
        </div>
      </form>
      
      {/* Example Prompts */}
      {!isLoading && prompt.length === 0 && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="flex flex-wrap gap-2 mt-6 justify-center"
        >
          {[
            "E-commerce with Stripe, cart, and admin panel",
            "SaaS platform with multi-tenant billing",
            "Healthcare booking app with patient history",
          ].map((example) => (
            <button
              key={example}
              onClick={() => setPrompt(example)}
              className="text-xs px-3 py-1.5 rounded-full bg-slate-800/50 text-slate-400 hover:bg-slate-700 hover:text-slate-200 border border-slate-700/50 transition-colors"
            >
              {example}
            </button>
          ))}
        </motion.div>
      )}
    </motion.div>
  );
}
