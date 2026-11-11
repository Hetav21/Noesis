"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, isNotFoundError, type ResearchJob } from "@/lib/api";
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
  Lock,
  Copy,
  FolderInput,
  X,
  AlertTriangle,
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
  const [errorType, setErrorType] = useState<"not_found" | "transient" | null>(
    null,
  );
  const [copiedLink, setCopiedLink] = useState(false);
  const [viewMode, setViewMode] = useState<WorkspaceViewMode>("report");
  const [isUpdatingVisibility, setIsUpdatingVisibility] = useState(false);
  const [visibilityError, setVisibilityError] = useState<string | null>(null);
  const [isForking, setIsForking] = useState(false);
  const [forkError, setForkError] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [retryTrigger, setRetryTrigger] = useState(0);
  const statusRef = useRef<string>("queued");
  const consecutiveErrorsRef = useRef<number>(0);
  const visibilityRequestIdRef = useRef<number>(0);

  const fetchJob = useCallback(
    async (showLoading = false): Promise<boolean> => {
      if (!jobId) return false;
      if (showLoading) setIsLoading(true);
      try {
        const data = await api.getResearch(jobId);
        consecutiveErrorsRef.current = 0;
        // Prevent stale responses from overwriting completed or terminal job state
        setJob((prev) => {
          if (prev?.status === "completed" && data.status !== "completed") {
            return prev;
          }
          return data;
        });
        statusRef.current = data.status;
        setError(null);
        setErrorType(null);

        // If job is still running, switch to activity view to observe progress
        if (data.status === "running" || data.status === "queued") {
          setViewMode((prev) => (prev === "report" ? "activity" : prev));
        } else if (data.status === "completed") {
          // Default to report view when completed
          setViewMode((prev) => (prev === "activity" ? "report" : prev));
        }
        setIsLoading(false);
        return false;
      } catch (err: unknown) {
        console.warn("Research job fetch notice:", err);
        const msg =
          err instanceof Error
            ? err.message
            : "Research session could not be retrieved.";
        const isNotFound = isNotFoundError(err);

        // 404 / private / missing session is terminal: stop polling immediately, clear loading, and show error
        if (isNotFound) {
          statusRef.current = "error";
          setError(msg);
          setErrorType("not_found");
          setIsLoading(false);
          return false;
        }

        // For transient errors (e.g. temporary network drop, 5xx server glitch):
        // Allow bounded consecutive retries without stopping polling or flipping
        // an active research session into an error screen.
        consecutiveErrorsRef.current += 1;
        const maxTransientRetries = 5;

        if (consecutiveErrorsRef.current >= maxTransientRetries) {
          statusRef.current = "error";
          setError(msg);
          setErrorType("transient");
          setIsLoading(false);
          return false;
        }

        // Return true to indicate a transient error occurred, allowing polling to back off
        return true;
      }
    },
    [jobId],
  );

  useEffect(() => {
    let timeoutId: NodeJS.Timeout | null = null;
    let isCancelled = false;

    consecutiveErrorsRef.current = 0;
    statusRef.current = "queued";

    const poll = async (isInitial = false) => {
      const isTransientError = await fetchJob(isInitial);
      if (
        !isCancelled &&
        (statusRef.current === "running" || statusRef.current === "queued")
      ) {
        // Schedule next poll after backoff delay on transient failure, or regular interval
        const delay = isTransientError ? 3000 : 1800;
        timeoutId = setTimeout(() => poll(false), delay);
      }
    };

    poll(true);

    return () => {
      isCancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [fetchJob, retryTrigger]);

  const tryFallbackCopy = () => {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = window.location.href;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      document.execCommand("copy");
      document.body.removeChild(textArea);
    } catch {
      // ignore clipboard fallback errors
    }
  };

  const handleCopyLink = () => {
    setCopyError(null);
    if (typeof window !== "undefined") {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);

      try {
        if (navigator?.clipboard?.writeText) {
          navigator.clipboard.writeText(window.location.href).catch(() => {
            tryFallbackCopy();
          });
        } else {
          tryFallbackCopy();
        }
      } catch {
        tryFallbackCopy();
      }
    }
  };

  const handleToggleVisibility = async () => {
    if (!job) return;
    const nextState = !job.is_public;
    const currentRequestId = ++visibilityRequestIdRef.current;
    setIsUpdatingVisibility(true);
    setVisibilityError(null);

    // Instant optimistic update (0ms UI latency)
    setJob((prev) => (prev ? { ...prev, is_public: nextState } : prev));

    try {
      const updated = await api.updateVisibility(job.id, nextState);
      if (visibilityRequestIdRef.current === currentRequestId) {
        setJob((prev) =>
          prev ? { ...prev, is_public: updated.is_public } : prev,
        );
      }
    } catch (err) {
      console.error("Failed to toggle visibility", err);
      if (visibilityRequestIdRef.current === currentRequestId) {
        // Rollback on failure
        setJob((prev) => (prev ? { ...prev, is_public: !nextState } : prev));
        setVisibilityError(
          err instanceof Error ? err.message : "Failed to update visibility.",
        );
      }
    } finally {
      if (visibilityRequestIdRef.current === currentRequestId) {
        setIsUpdatingVisibility(false);
      }
    }
  };

  const handleFork = async () => {
    if (!job || isForking) return;
    setIsForking(true);
    setForkError(null);
    try {
      const cloned = await api.forkResearch(job.id);
      router.push(`/research/${cloned.id}`);
    } catch (err: unknown) {
      console.error("Failed to import research session", err);
      setForkError(
        err instanceof Error ? err.message : "Failed to import research session.",
      );
    } finally {
      setIsForking(false);
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
    const isTransient = errorType === "transient";

    return (
      <div className="max-w-md mx-auto my-auto p-8 text-center space-y-5">
        <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-white/[0.08] flex items-center justify-center mx-auto text-zinc-400">
          {isTransient ? (
            <AlertTriangle className="w-5 h-5 text-amber-400" />
          ) : (
            <Lock className="w-5 h-5 text-zinc-400" />
          )}
        </div>
        <div className="space-y-1.5">
          <h2 className="text-lg font-semibold text-zinc-100">
            {isTransient
              ? "Unable to Connect to Research Session"
              : "Research Not Found or Private"}
          </h2>
          <p className="text-xs text-zinc-400 leading-relaxed">
            {error ||
              (isTransient
                ? "The research server is temporarily unreachable. Check your connection or retry."
                : "This research session does not exist, has been deleted, or is set to private by its author.")}
          </p>
        </div>
        <div className="flex items-center justify-center gap-2.5">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setRetryTrigger((prev) => prev + 1)}
            leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
          >
            Retry
          </Button>
          <Button
            size="sm"
            onClick={() => router.push("/")}
            leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
          >
            Start New Research
          </Button>
        </div>
      </div>
    );
  }

  const isCompleted = job.status === "completed";
  const isOwner = job.is_owner !== false;

  return (
    <div className="flex-1 flex flex-col max-w-5xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
      {/* Workspace Header */}
      <div className="space-y-4">
        {/* Navigation & Actions Row */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Research</span>
          </Link>

          {isCompleted && (
            <div className="flex items-center gap-2">
              {isOwner ? (
                <div className="flex items-center gap-2">
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleCopyLink}
                    className="bg-white hover:bg-zinc-100 text-zinc-950 font-medium shadow-sm border border-white/20"
                    leftIcon={
                      copiedLink ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Share2 className="w-3.5 h-3.5 text-zinc-900" />
                      )
                    }
                  >
                    {copiedLink ? "Copied" : "Share"}
                  </Button>

                  {/* Public Toggle */}
                  <div
                    role="button"
                    tabIndex={0}
                    onClick={handleToggleVisibility}
                    onKeyDown={(e) => {
                      if (e.key === " " || e.key === "Enter") {
                        e.preventDefault();
                        handleToggleVisibility();
                      }
                    }}
                    className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800/80 border border-white/[0.08] hover:border-white/[0.15] text-xs select-none cursor-pointer transition-colors focus:outline-none focus-visible:ring-1 focus-visible:ring-zinc-400"
                  >
                    <span className="text-xs font-medium text-zinc-300">Public</span>
                    <span
                      role="switch"
                      aria-checked={job.is_public}
                      aria-busy={isUpdatingVisibility}
                      aria-label="Toggle public link sharing"
                      className={`relative inline-flex h-5 w-9 shrink-0 rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                        job.is_public ? "bg-emerald-500" : "bg-zinc-700"
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${
                          job.is_public ? "translate-x-4" : "translate-x-0"
                        }`}
                      />
                    </span>
                  </div>
                </div>
              ) : (
                <>
                  <Button
                    variant="default"
                    size="sm"
                    isLoading={isForking}
                    onClick={handleFork}
                    leftIcon={<FolderInput className="w-3.5 h-3.5" />}
                    className="bg-white text-zinc-950 hover:bg-zinc-100 shadow-sm font-medium"
                  >
                    Import to my sessions
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyLink}
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
                </>
              )}
            </div>
          )}
        </div>

        {/* Visibility Error Notice */}
        {visibilityError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
            <span>{visibilityError}</span>
            <button
              aria-label="Dismiss error"
              onClick={() => setVisibilityError(null)}
              className="text-rose-400 hover:text-rose-200 p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Fork Error Notice if any */}
        {forkError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
            <span>{forkError}</span>
            <button
              aria-label="Dismiss error"
              onClick={() => setForkError(null)}
              className="text-rose-400 hover:text-rose-200 p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Copy Error Notice if any */}
        {copyError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-center justify-between">
            <span>{copyError}</span>
            <button
              aria-label="Dismiss error"
              onClick={() => setCopyError(null)}
              className="text-rose-400 hover:text-rose-200 p-1"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

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
          {(isCompleted || job.status === "failed") && (
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
