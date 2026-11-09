"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const isHome = pathname === "/";

  return (
    <header className="sticky top-0 z-50 w-full backdrop-blur-md bg-[#09090b]/80 border-b border-white/[0.06]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-zinc-100 hover:text-white transition-colors"
        >
          <span className="font-semibold text-sm tracking-tight">
            Deep Research
          </span>
        </Link>

        <div className="flex items-center gap-3">
          {!isHome && (
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-white/[0.08] text-zinc-200 text-xs font-medium transition-[background-color,transform] active:scale-[0.98]"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Search</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};
