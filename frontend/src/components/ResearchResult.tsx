"use client";

import React, { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { Button } from "./ui/button";
import {
  Copy,
  Check,
  Download,
  BookOpen,
  Clock,
  ExternalLink,
  ListTree,
} from "lucide-react";

interface ResearchResultProps {
  result: string | null;
  status: string;
  query: string;
  jobId?: string;
  sourcesCount?: number;
  depth?: number;
  onViewActivity?: () => void;
  fullHeight?: boolean;
}

export const ResearchResult: React.FC<ResearchResultProps> = ({
  result,
  status,
  query,
  jobId,
  sourcesCount = 0,
  depth = 2,
  onViewActivity,
  fullHeight = false,
}) => {
  const [copied, setCopied] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  // Stats calculation
  const stats = useMemo(() => {
    if (!result) return { words: 0, readTime: 0 };
    const words = result.trim().split(/\s+/).filter(Boolean).length;
    const readTime = Math.max(1, Math.ceil(words / 220));
    return { words, readTime };
  }, [result]);

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy", err);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    try {
      const sanitizedName = query
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .slice(0, 40)
        .replace(/^-|-$/g, "");
      const filename = `research-${sanitizedName || "report"}.md`;
      const blob = new Blob([result], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setDownloaded(true);
      setTimeout(() => setDownloaded(false), 2000);
    } catch (err) {
      console.error("Failed to download", err);
    }
  };

  return (
    <Card
      className={`border-white/[0.08] ${fullHeight ? "min-h-[500px]" : "h-full flex flex-col min-h-0"}`}
    >
      <CardHeader className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            {jobId ? (
              <a
                href={`/research/${jobId}/raw`}
                target="_blank"
                rel="noopener noreferrer"
                title="Open report in new tab"
                className="group inline-flex items-center gap-1.5 text-zinc-100 hover:text-white transition-colors"
              >
                <CardTitle className="leading-none group-hover:text-white transition-colors">
                  Report
                </CardTitle>
                <ExternalLink className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200 transition-colors shrink-0" />
              </a>
            ) : (
              <CardTitle className="leading-none">Report</CardTitle>
            )}
          </div>
          {result && (
            <div className="flex items-center gap-3 mt-1 text-xs text-zinc-400 font-mono">
              <span className="flex items-center gap-1">
                <BookOpen className="w-3 h-3 text-zinc-500" />
                {stats.words.toLocaleString()} words
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3 text-zinc-500" />~{stats.readTime} min
                read
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {result && (
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              leftIcon={
                copied ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )
              }
            >
              {copied ? "Copied" : "Copy"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownload}
              leftIcon={
                downloaded ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Download className="w-3.5 h-3.5" />
                )
              }
            >
              {downloaded ? "Saved" : "Export .md"}
            </Button>
          </div>
        )}
      </CardHeader>

      <CardContent
        className={`p-0 flex flex-col ${fullHeight ? "" : "flex-1 min-h-0 overflow-hidden"}`}
      >
        {/* Subtle Process Strip */}
        {result && onViewActivity && (
          <div className="px-6 py-2.5 bg-zinc-900/60 border-b border-white/[0.04] flex items-center justify-between text-xs text-zinc-400">
            <span className="font-mono text-[11px] text-zinc-400">
              Researched across {depth} {depth === 1 ? "round" : "rounds"} •{" "}
              {sourcesCount > 0
                ? `${sourcesCount} events recorded`
                : "Multiple web sources"}
            </span>
            <button
              type="button"
              onClick={onViewActivity}
              className="inline-flex items-center gap-1 text-xs text-zinc-300 hover:text-white transition-colors cursor-pointer"
            >
              <ListTree className="w-3.5 h-3.5" />
              <span>Inspect activity</span>
            </button>
          </div>
        )}

        <div
          className={`p-6 sm:p-8 bg-[#0e0e11] ${fullHeight ? "" : "flex-1 overflow-y-auto"}`}
        >
          {result ? (
            <div className="markdown-body max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-center p-6 space-y-3">
              <div className="space-y-1 max-w-sm">
                <h4 className="font-medium text-zinc-300 text-sm">
                  {status === "running"
                    ? "Generating report..."
                    : status === "queued"
                      ? "In queue"
                      : "Report pending"}
                </h4>
                <p className="text-xs text-zinc-500 leading-relaxed">
                  {status === "running"
                    ? "Synthesizing gathered search evidence into a structured markdown report."
                    : "The final report will appear here once research completes."}
                </p>
              </div>

              {/* Minimal clean skeleton pulse */}
              {status === "running" && (
                <div className="w-full max-w-sm pt-4 space-y-2 opacity-30">
                  <div className="h-3 bg-zinc-700 rounded-full w-4/5 animate-pulse" />
                  <div className="h-3 bg-zinc-700 rounded-full w-full animate-pulse" />
                  <div className="h-3 bg-zinc-700 rounded-full w-2/3 animate-pulse" />
                </div>
              )}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
