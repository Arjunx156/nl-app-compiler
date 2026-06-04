import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { Sparkles, History, Activity } from "lucide-react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Antigravity | NL App Compiler",
  description: "Natural Language to Full Application Schema Compiler",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-[#0a0a0a] text-[#f5f5f5] antialiased selection:bg-[#7c3aed]/30`}>
        {/* Global Navigation */}
        <nav className="fixed top-0 left-0 right-0 h-16 bg-[#0a0a0a]/80 backdrop-blur-md border-b border-[#1f1f1f] z-50 flex items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-2 group">
            <div className="bg-gradient-to-br from-[#7c3aed] to-[#3b82f6] p-1.5 rounded-lg group-hover:shadow-[0_0_15px_rgba(124,58,237,0.5)] transition-all">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold tracking-tight text-lg">App<span className="text-[#7c3aed]">Compiler</span></span>
          </Link>
          
          <div className="flex items-center gap-6">
            <Link href="/" className="text-sm font-medium text-[#a3a3a3] hover:text-[#f5f5f5] transition-colors flex items-center gap-2">
              Generator
            </Link>
            <Link href="/history" className="text-sm font-medium text-[#a3a3a3] hover:text-[#f5f5f5] transition-colors flex items-center gap-2">
              <History className="w-4 h-4" /> History
            </Link>
            <Link href="/eval" className="text-sm font-medium text-[#a3a3a3] hover:text-[#f5f5f5] transition-colors flex items-center gap-2">
              <Activity className="w-4 h-4" /> Evaluation
            </Link>
          </div>
        </nav>
        
        {children}
      </body>
    </html>
  );
}
