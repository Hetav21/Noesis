"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, type ResearchJob } from "@/lib/api";
import { ResearchLog } from "@/components/ResearchLog";
import { ResearchResult } from "@/components/ResearchResult";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Share2,
  Check,
  Clock,
  RotateCcw,
  FileText,
  Activity,
  Columns2,
} from "lucide-react";

interface ResearchWorkspaceProps {
  jobId: string;
}

type WorkspaceViewMode = "report" | "activity" | "split";

export const ResearchWorkspace: React.FC<ResearchWorkspaceProps> = ({
  jobId,
}) => {
  const router = useRouter();
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);
  const [viewMode, setViewMode] = useState<WorkspaceViewMode>("report");
  const statusRef = useRef<string>("queued");

  const fetchJob = useCallback(
    async (showLoading = false) => {
      if (!jobId) return;
      if (showLoading) setIsLoading(true);
      try {
        const data = await api.getResearch(jobId);
        setJob(data);
        statusRef.current = data.status;
        setError(null);

        // If job is still running, switch to activity view to observe progress
        if (data.status === "running" || data.status === "queued") {
          setViewMode((prev) => (prev === "report" ? "activity" : prev));
        } else if (data.status === "completed") {
          // Default to report view when completed
          setViewMode((prev) => (prev === "activity" ? "report" : prev));
        }
      } catch (err: unknown) {
        console.warn("Research job fetch notice:", err);
        setError("Research session could not be retrieved.");
      } finally {
        if (showLoading) setIsLoading(false);
      }
    },
    [jobId],
  );

  useEffect(() => {
    fetchJob(true);

    const interval = setInterval(() => {
      if (statusRef.current === "running" || statusRef.current === "queued") {
        fetchJob(false);
      } else {
        clearInterval(interval);
      }
    }, 1800);

    return () => clearInterval(interval);
  }, [fetchJob]);

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch (err) {
      console.error("Failed to copy share link", err);
    }
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "completed":
        return (
          <Badge variant="success" dot>
            Completed
          </Badge>
        );
      case "running":
        return (
          <Badge variant="warning" dot pulse>
            In Progress
          </Badge>
        );
      case "failed":
        return (
          <Badge variant="danger" dot>
            Failed
          </Badge>
        );
      case "queued":
      default:
        return (
          <Badge variant="neutral" dot pulse>
            Queued
          </Badge>
        );
    }
  };

  if (isLoading && !job) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-3">
        <div className="w-5 h-5 border-2 border-zinc-700 border-t-zinc-200 rounded-full animate-spin" />
        <p className="text-xs text-zinc-500 font-mono">
          Loading session #{jobId?.slice(0, 8)}...
        </p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-md mx-auto my-auto p-8 text-center space-y-5">
        <div className="space-y-1.5">
          <h2 className="text-lg font-semibold text-zinc-100">
            Session Not Available
          </h2>
          <p className="text-xs text-zinc-400 leading-relaxed">
            {error ||
              "This research session does not exist or has been removed."}
          </p>
        </div>
        <div className="flex items-center justify-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => fetchJob(true)}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Retry
          </Button>
          <Button
            size="sm"
            onClick={() => router.push("/")}
            leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Dashboard
          </Button>
        </div>
      </div>
    );
  }

  const isCompleted = job.status === "completed";

  return (
    <div className="flex-1 flex flex-col max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Workspace Header */}
      <div className="space-y-4">
        {/* Navigation & Actions Row */}
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Research</span>
          </Link>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              leftIcon={
                copiedLink ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Share2 className="w-3.5 h-3.5" />
                )
              }
            >
              {copiedLink ? "Copied" : "Share"}
            </Button>
          </div>
        </div>

        {/* Title & Metadata Card */}
        <div className="p-5 sm:p-6 rounded-2xl bg-[#121215] border border-white/[0.08] space-y-3">
          <div className="flex items-center gap-2.5 flex-wrap">
            {getStatusBadge(job.status)}
            <span className="text-[11px] text-zinc-500 font-mono flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(job.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </span>
            <span className="text-[11px] text-zinc-500 font-mono">
              • {job.depth} {job.depth === 1 ? "round" : "rounds"} •{" "}
              {job.breadth} sources/query
            </span>
          </div>

          <h1 className="text-xl sm:text-2xl font-bold text-white tracking-tight leading-snug">
            {job.query}
          </h1>

          {/* View Mode Switcher */}
          {isCompleted && (
            <div className="pt-2 flex items-center justify-between gap-3 border-t border-white/[0.06]">
              <div className="flex items-center gap-1 bg-zinc-900/90 p-1 rounded-xl border border-white/[0.06] text-xs">
                <button
                  type="button"
                  onClick={() => setViewMode("report")}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                    viewMode === "report"
                      ? "bg-zinc-800 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Report</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("activity")}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                    viewMode === "activity"
                      ? "bg-zinc-800 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <Activity className="w-3.5 h-3.5" />
                  <span>Activity ({job.logs?.length || 0})</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode("split")}
                  className={`hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-colors cursor-pointer ${
                    viewMode === "split"
                      ? "bg-zinc-800 text-white shadow-sm"
                      : "text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  <Columns2 className="w-3.5 h-3.5" />
                  <span>Split View</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {viewMode === "report" ? (
        /* Full-Width Editorial Report View */
        <div className="w-full">
          <ResearchResult
            result={job.result}
            status={job.status}
            query={job.query}
            jobId={job.id}
            sourcesCount={job.logs?.length || 0}
            depth={job.depth}
            onViewActivity={() => setViewMode("activity")}
            fullHeight={true}
          />
        </div>
      ) : viewMode === "activity" ? (
        /* Full-Width Activity Stream */
        <div className="w-full min-h-[600px] h-[calc(100vh-280px)]">
          <ResearchLog logs={job.logs || []} status={job.status} />
        </div>
      ) : (
        /* Side by Side Split View (on wide displays) */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100vh-280px)] min-h-[600px] overflow-hidden">
          <div className="lg:col-span-5 h-full min-h-0 flex flex-col overflow-hidden">
            <ResearchLog logs={job.logs || []} status={job.status} />
          </div>
          <div className="lg:col-span-7 h-full min-h-0 flex flex-col overflow-hidden">
            <ResearchResult
              result={job.result}
              status={job.status}
              query={job.query}
              jobId={job.id}
              sourcesCount={job.logs?.length || 0}
              depth={job.depth}
              fullHeight={false}
            />
          </div>
        </div>
      )}
    </div>
  );
};
