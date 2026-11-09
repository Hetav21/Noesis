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
          className="flex items-center gap-2.5 text-zinc-100 hover:text-white transition-colors"
        >
          <svg
            className="w-5 h-5 flex-shrink-0"
            viewBox="0 0 32 32"
            fill="none"
          >
            <rect width="32" height="32" rx="7" fill="#18181b" stroke="#27272a" strokeWidth="1" />
            <polygon points="16,6.5 24.5,11.25 16,16 7.5,11.25" fill="#27272a" stroke="#3f3f46" strokeWidth="1" strokeLinejoin="round" />
            <polygon points="7.5,11.25 16,16 16,25.5 7.5,20.75" fill="#09090b" stroke="#27272a" strokeWidth="1" strokeLinejoin="round" />
            <polygon points="16,16 24.5,11.25 24.5,20.75 16,25.5" fill="#121216" stroke="#27272a" strokeWidth="1" strokeLinejoin="round" />
            <path d="M16 16V4" stroke="#818cf8" strokeWidth="2" strokeLinecap="round" />
            <circle cx="16" cy="4" r="1.2" fill="#ffffff" />
            <path d="M7.5 20.75V11.25L16 16L24.5 20.75V11.25" stroke="#f4f4f5" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="16" cy="16" r="1.25" fill="#818cf8" />
          </svg>
          <span className="font-semibold text-sm tracking-tight">Noesis</span>
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
