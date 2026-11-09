"use client";

import React, { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { Button } from "./ui/button";
import { AiSuggestions } from "./AiSuggestions";
import { ArrowUp, SlidersHorizontal, ChevronDown } from "lucide-react";

interface ResearchFormProps {
  onSubmit: (query: string, depth: number, breadth: number) => void;
  isLoading: boolean;
}

const DEFAULT_SUGGESTIONS = [
  "Solid-state vs sodium-ion battery commercial viability",
  "Post-quantum cryptography migration for TLS 1.3",
  "Agentic orchestration patterns vs deterministic DAGs",
  "WebAssembly component model in serverless runtimes",
];

type DepthPreset = "quick" | "standard" | "deep" | "custom";

export const ResearchForm: React.FC<ResearchFormProps> = ({
  onSubmit,
  isLoading,
}) => {
  const [query, setQuery] = useState("");
  const [preset, setPreset] = useState<DepthPreset>("standard");
  const [depth, setDepth] = useState<number>(2);
  const [breadth, setBreadth] = useState<number>(4);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS);
  const [isRefreshingSuggestions, setIsRefreshingSuggestions] = useState(false);
  const isFetchingRef = React.useRef(false);

  // Restore cached suggestions from sessionStorage on client mount to eliminate initial flash
  useEffect(() => {
    try {
      const cached = sessionStorage.getItem("noesis_suggestions");
      if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSuggestions(parsed);
        }
      }
    } catch {
      // ignore
    }
  }, []);

  const fetchSuggestions = async (forceRefresh: boolean = false) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    setIsRefreshingSuggestions(true);
    try {
      const items = await api.getSuggestions(forceRefresh);
      if (items && items.length > 0) {
        setSuggestions((prev) => {
          const isSame =
            prev.length === items.length &&
            prev.every((val, idx) => val === items[idx]);
          if (isSame) return prev;
          try {
            sessionStorage.setItem(
              "noesis_suggestions",
              JSON.stringify(items),
            );
          } catch {
            // ignore
          }
          return items;
        });
      }
    } catch (err) {
      console.warn("Failed to refresh suggestions", err);
    } finally {
      isFetchingRef.current = false;
      setIsRefreshingSuggestions(false);
    }
  };

  // Fetch AI suggestions on mount (cached on backend, avoids duplicate strict mode calls)
  useEffect(() => {
    fetchSuggestions(false);
  }, []);

  const handlePresetSelect = (p: DepthPreset) => {
    setPreset(p);
    if (p === "quick") {
      setDepth(1);
      setBreadth(3);
      setShowAdvanced(false);
    } else if (p === "standard") {
      setDepth(2);
      setBreadth(4);
      setShowAdvanced(false);
    } else if (p === "deep") {
      setDepth(3);
      setBreadth(6);
      setShowAdvanced(false);
    } else if (p === "custom") {
      setShowAdvanced(true);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim(), depth, breadth);
    }
  };

  return (
    <div className="space-y-3.5">
      <form onSubmit={handleSubmit}>
        <div className="relative rounded-2xl bg-[#121215] border border-white/[0.1] focus-within:border-white/25 focus-within:ring-1 focus-within:ring-white/20 transition-[border-color,box-shadow] shadow-xl shadow-black/20 overflow-hidden">
          {/* Main Query Textarea */}
          <textarea
            id="query"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (
                e.key === "Enter" &&
                !e.shiftKey &&
                !e.nativeEvent.isComposing
              ) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            placeholder="Ask a question, research a topic, or compare technologies..."
            disabled={isLoading}
            className="w-full bg-transparent text-zinc-100 placeholder-zinc-500 px-5 pt-4 pb-2 text-sm sm:text-base focus:outline-none disabled:opacity-50 resize-none leading-relaxed"
          />

          {/* Integrated Bottom Action Bar */}
          <div className="px-3.5 pb-3 pt-2 flex items-center justify-between gap-2 border-t border-white/[0.04] bg-[#0f0f12]">
            {/* Depth Selector Pills + Advanced Options */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <div className="flex items-center gap-1 bg-zinc-900/90 p-0.5 rounded-lg border border-white/[0.06]">
                <button
                  type="button"
                  onClick={() => handlePresetSelect("quick")}
                  disabled={isLoading}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    preset === "quick" && !showAdvanced
                      ? "bg-zinc-800 text-zinc-100 shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Quick{" "}
                  <span className="text-[10px] text-zinc-500 hidden sm:inline ml-1">
                    1 round
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => handlePresetSelect("standard")}
                  disabled={isLoading}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    preset === "standard" && !showAdvanced
                      ? "bg-zinc-800 text-zinc-100 shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Standard{" "}
                  <span className="text-[10px] text-zinc-500 hidden sm:inline ml-1">
                    2 rounds
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => handlePresetSelect("deep")}
                  disabled={isLoading}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                    preset === "deep" && !showAdvanced
                      ? "bg-zinc-800 text-zinc-100 shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  Deep{" "}
                  <span className="text-[10px] text-zinc-500 hidden sm:inline ml-1">
                    3 rounds
                  </span>
                </button>
              </div>

              {/* Advanced Options Toggle */}
              <button
                type="button"
                onClick={() => {
                  setShowAdvanced(!showAdvanced);
                  if (!showAdvanced) setPreset("custom");
                }}
                disabled={isLoading}
                className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors cursor-pointer ${
                  showAdvanced
                    ? "bg-zinc-800 border-white/20 text-zinc-100"
                    : "bg-zinc-900/70 border-white/[0.06] text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <SlidersHorizontal className="w-3 h-3" />
                <span>Advanced</span>
                <ChevronDown
                  className={`w-3 h-3 transition-transform duration-150 ${
                    showAdvanced ? "rotate-180" : ""
                  }`}
                />
              </button>
            </div>

            {/* Run Button (no redundant 'Press Enter' text) */}
            <Button
              type="submit"
              size="sm"
              disabled={!query.trim() || isLoading}
              isLoading={isLoading}
              className="h-8 px-3 rounded-lg"
            >
              {!isLoading && (
                <>
                  <span className="text-xs font-medium">Search</span>
                  <ArrowUp className="w-3.5 h-3.5 ml-1" />
                </>
              )}
            </Button>
          </div>

          {/* Advanced Drawer with Sliders & Manual Inputs */}
          {showAdvanced && (
            <div className="p-4 sm:p-5 border-t border-white/[0.06] bg-[#0b0b0e] space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                {/* Custom Depth Slider + Manual Input */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <label
                      id="depth-label"
                      htmlFor="depth-input"
                      className="text-zinc-200 font-medium"
                    >
                      Follow-up Rounds (Depth)
                    </label>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-zinc-500 font-mono">
                        1 – 5
                      </span>
                      <input
                        id="depth-input"
                        type="number"
                        min={1}
                        max={5}
                        value={depth}
                        onChange={(e) => {
                          const val = parseInt(e.target.value, 10);
                          if (!isNaN(val)) {
                            setDepth(Math.min(5, Math.max(1, val)));
                            setPreset("custom");
                          }
                        }}
                        className="w-12 px-2 py-0.5 text-center font-mono text-xs bg-zinc-900 border border-white/[0.12] rounded-md text-white focus:outline-none focus:border-zinc-400 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      id="depth-slider"
                      type="range"
                      min={1}
                      max={5}
                      step={1}
                      value={depth}
                      aria-labelledby="depth-label"
                      onChange={(e) => {
                        setDepth(Number(e.target.value));
                        setPreset("custom");
                      }}
                      className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-zinc-200"
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-zinc-500 font-mono px-0.5">
                    <span>1 (Fast)</span>
                    <span>3 (Balanced)</span>
                    <span>5 (Comprehensive)</span>
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-relaxed">
                    Controls how many iterative re-query and evidence evaluation
                    cycles are executed.
                  </p>
                </div>

                {/* Custom Breadth Slider + Manual Input */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <label
                      id="breadth-label"
                      htmlFor="breadth-input"
                      className="text-zinc-200 font-medium"
                    >
                      Sources per Query (Breadth)
                    </label>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-zinc-500 font-mono">
                        2 – 10
                      </span>
                      <input
                        id="breadth-input"
                        type="number"
                        min={2}
                        max={10}
                        value={breadth}
                        onChange={(e) => {
                          const val = parseInt(e.target.value, 10);
                          if (!isNaN(val)) {
                            setBreadth(Math.min(10, Math.max(2, val)));
                            setPreset("custom");
                          }
                        }}
                        className="w-12 px-2 py-0.5 text-center font-mono text-xs bg-zinc-900 border border-white/[0.12] rounded-md text-white focus:outline-none focus:border-zinc-400 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      id="breadth-slider"
                      type="range"
                      min={2}
                      max={10}
                      step={1}
                      value={breadth}
                      aria-labelledby="breadth-label"
                      onChange={(e) => {
                        setBreadth(Number(e.target.value));
                        setPreset("custom");
                      }}
                      className="w-full h-1.5 bg-zinc-800 rounded-lg appearance-none cursor-pointer accent-zinc-200"
                    />
                  </div>
                  <div className="flex justify-between text-[10px] text-zinc-500 font-mono px-0.5">
                    <span>2 sources</span>
                    <span>6 sources</span>
                    <span>10 sources</span>
                  </div>
                  <p className="text-[10px] text-zinc-500 leading-relaxed">
                    Maximum live web results scraped and analyzed for each
                    generated sub-query.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </form>

      {/* Dynamic AI-Generated Topic Suggestions with Aceternity Animation */}
      <AiSuggestions
        suggestions={suggestions}
        onSelect={(selected) => setQuery(selected)}
        onRefresh={() => fetchSuggestions(true)}
        isLoading={isRefreshingSuggestions}
      />
    </div>
  );
};
