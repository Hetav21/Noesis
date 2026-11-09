"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import type { LogEvent } from "@/lib/api";
import { ExternalLink, ArrowDown, Layers } from "lucide-react";

interface ResearchLogProps {
  logs: LogEvent[];
  status: string;
}

export const ResearchLog: React.FC<ResearchLogProps> = ({ logs, status }) => {
  const logEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState<"all" | "reasoning" | "sources">("all");

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 40;
    setAutoScroll(isAtBottom);
  };

  const filteredLogs = useMemo(() => {
    if (filter === "all") return logs;
    return logs.filter((log) => {
      const msg = (log.message || log.title || log.content || "").toLowerCase();
      if (filter === "sources") {
        return (
          msg.includes("url:") ||
          msg.includes("searching for:") ||
          msg.includes("result:") ||
          msg.includes("summary:")
        );
      }
      if (filter === "reasoning") {
        return (
          msg.includes("thoughts:") ||
          msg.includes("reasoning:") ||
          msg.includes("decision:")
        );
      }
      return true;
    });
  }, [logs, filter]);

  // Derive current phase
  const currentPhase = useMemo(() => {
    if (status === "completed") return "Finished";
    if (status === "failed") return "Failed";
    if (logs.length === 0) return "Starting...";

    const lastLog = logs[logs.length - 1];
    const lastMsg = (lastLog?.message || lastLog?.title || "").toLowerCase();
    if (lastMsg.includes("synthesis") || lastMsg.includes("synthesizing"))
      return "Writing report...";
    if (lastMsg.includes("evaluating") || lastMsg.includes("follow-up"))
      return "Evaluating findings...";
    if (lastMsg.includes("analyzing") || lastMsg.includes("summary:"))
      return "Analyzing sources...";
    if (lastMsg.includes("searching")) return "Searching the web...";
    if (lastMsg.includes("query")) return "Generating queries...";
    return "In progress";
  }, [logs, status]);

  const renderLogMessage = (log: LogEvent) => {
    const rawMessage = (
      log.message ||
      log.title ||
      log.content ||
      ""
    ).toString();

    // Section header
    if (log.type === "section" || (!log.message && log.title)) {
      return (
        <div className="text-[11px] font-mono uppercase tracking-wider text-zinc-300 font-semibold py-1">
          {log.title || rawMessage}
        </div>
      );
    }

    // Source URL
    if (rawMessage.startsWith("URL: ")) {
      const url = rawMessage.replace("URL: ", "").trim();
      let hostname: string;
      try {
        hostname = new URL(url).hostname;
      } catch {
        hostname = url;
      }
      return (
        <div className="flex items-center gap-2 overflow-hidden text-xs">
          <span className="text-zinc-500 font-mono text-[11px]">SOURCE</span>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-zinc-300 hover:text-white underline underline-offset-2 flex items-center gap-1 truncate font-mono text-xs"
          >
            <span>{hostname}</span>
            <ExternalLink className="w-3 h-3 text-zinc-500 shrink-0" />
          </a>
        </div>
      );
    }

    // Crawl target
    if (rawMessage.startsWith("Result: ")) {
      return (
        <div className="text-xs text-zinc-300">
          <span className="text-zinc-500 font-mono text-[11px] mr-1.5">
            RESULT
          </span>
          <span className="font-medium text-zinc-200">
            {rawMessage.replace("Result: ", "")}
          </span>
        </div>
      );
    }

    // Agent Internal Reasoning / Thoughts
    if (
      rawMessage.startsWith("Thoughts: ") ||
      rawMessage.startsWith("Reasoning: ")
    ) {
      const isThoughts = rawMessage.startsWith("Thoughts: ");
      const content = rawMessage.replace(
        isThoughts ? "Thoughts: " : "Reasoning: ",
        "",
      );
      return (
        <div className="p-3 rounded-lg bg-zinc-900 border-l-2 border-zinc-600 border-y border-r border-white/[0.05] text-xs text-zinc-300 space-y-1">
          <div className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 font-medium">
            Reasoning
          </div>
          <p className="leading-relaxed text-zinc-300">{content}</p>
        </div>
      );
    }

    // Agent Decision
    if (rawMessage.startsWith("Decision: ")) {
      return (
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-800 border border-white/[0.08] text-xs font-mono text-zinc-300">
          <span className="text-zinc-500">DECISION:</span>
          <span>{rawMessage.replace("Decision: ", "")}</span>
        </div>
      );
    }

    // Scraped content extract
    if (rawMessage.startsWith("Summary: ")) {
      return (
        <div className="p-2.5 rounded-lg bg-zinc-900/60 border border-white/[0.05] text-xs text-zinc-400 font-mono leading-relaxed">
          <span className="text-zinc-500">EXTRACT: </span>
          {rawMessage.replace("Summary: ", "")}
        </div>
      );
    }

    // Search query
    if (rawMessage.startsWith("Searching for: ")) {
      return (
        <div className="text-xs text-zinc-200 flex items-center gap-1.5">
          <span className="text-zinc-500 font-mono text-[11px]">QUERY</span>
          <span className="font-mono text-zinc-300">
            {rawMessage.replace("Searching for: ", "")}
          </span>
        </div>
      );
    }

    return (
      <span className="text-xs text-zinc-300 leading-relaxed">
        {rawMessage}
      </span>
    );
  };

  return (
    <Card className="h-full flex flex-col border-white/[0.08] min-h-0">
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <CardTitle>Activity</CardTitle>
            <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-400 border border-white/[0.06]">
              {logs.length}
            </span>
          </div>
          <p className="text-xs text-zinc-400 flex items-center gap-1.5 mt-0.5 font-normal">
            <Layers className="w-3 h-3 text-zinc-500" />
            {currentPhase}
          </p>
        </div>

        {/* Filter and control buttons */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-zinc-900 p-0.5 rounded-lg border border-white/[0.06] text-xs">
            <button
              onClick={() => setFilter("all")}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer text-xs ${
                filter === "all"
                  ? "bg-zinc-800 text-zinc-100 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter("reasoning")}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer text-xs ${
                filter === "reasoning"
                  ? "bg-zinc-800 text-zinc-100 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Reasoning
            </button>
            <button
              onClick={() => setFilter("sources")}
              className={`px-2.5 py-1 rounded-md transition-colors cursor-pointer text-xs ${
                filter === "sources"
                  ? "bg-zinc-800 text-zinc-100 font-medium"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              Sources
            </button>
          </div>

          {!autoScroll && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setAutoScroll(true);
                if (containerRef.current) {
                  containerRef.current.scrollTop =
                    containerRef.current.scrollHeight;
                }
              }}
              leftIcon={<ArrowDown className="w-3 h-3" />}
              className="text-xs h-7 px-2"
            >
              Follow
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 p-0 flex flex-col min-h-0 overflow-hidden">
        <div
          ref={containerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-2 bg-[#0d0d10] font-sans text-xs select-text"
        >
          {logs.length === 0 ? (
            <div className="h-full min-h-[250px] flex flex-col items-center justify-center text-center text-zinc-500 space-y-1.5">
              <p className="text-xs font-medium text-zinc-400">
                Awaiting agent workflow initialization
              </p>
              <p className="text-[11px] text-zinc-500 max-w-xs">
                Query decomposition and search execution events will stream here
                live.
              </p>
            </div>
          ) : (
            filteredLogs.map((log, index) => (
              <div
                key={index}
                className="p-3 rounded-xl bg-zinc-900/50 border border-white/[0.04] hover:border-white/[0.08] transition-colors flex flex-col gap-1.5"
              >
                <div className="flex items-center justify-between text-[11px] text-zinc-500">
                  <span className="font-mono text-zinc-500">
                    {new Date(log.timestamp).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </span>
                  <span className="text-[10px] text-zinc-600 font-mono">
                    #{index + 1}
                  </span>
                </div>
                <div>{renderLogMessage(log)}</div>
              </div>
            ))
          )}
          <div ref={logEndRef} />
        </div>
      </CardContent>
    </Card>
  );
};
