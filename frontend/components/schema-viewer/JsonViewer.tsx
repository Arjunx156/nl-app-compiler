"use client";

import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from "lucide-react";
import { useState } from "react";

export function JsonViewer({ data }: { data: any }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative h-full flex flex-col">
      <div className="absolute top-4 right-4 z-10">
        <button 
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 bg-[#1f1f1f] hover:bg-[#333] border border-[#333] rounded text-xs font-medium text-[#f5f5f5] transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-[#10b981]" /> : <Copy className="w-3 h-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <div className="flex-1 overflow-auto bg-[#1e1e1e]">
        <SyntaxHighlighter
          language="json"
          style={vscDarkPlus}
          customStyle={{ margin: 0, padding: '2rem', background: 'transparent', fontSize: '13px' }}
          showLineNumbers={true}
        >
          {JSON.stringify(data, null, 2)}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
