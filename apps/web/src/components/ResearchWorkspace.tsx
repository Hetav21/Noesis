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
  Globe,
  Copy,
  FolderInput,
  X,
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
  const [isShareOpen, setIsShareOpen] = useState(false);
  const [isUpdatingVisibility, setIsUpdatingVisibility] = useState(false);
  const [visibilityError, setVisibilityError] = useState<string | null>(null);
  const [isForking, setIsForking] = useState(false);
  const [forkError, setForkError] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [retryTrigger, setRetryTrigger] = useState(0);
  const statusRef = useRef<string>("queued");
  const consecutiveErrorsRef = useRef<number>(0);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

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

  useEffect(() => {
    if (!isShareOpen) return;

    previousFocusRef.current = document.activeElement as HTMLElement | null;

    const focusableSelector =
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

    const focusTimer = setTimeout(() => {
      if (dialogRef.current) {
        const firstFocusable =
          dialogRef.current.querySelector<HTMLElement>(focusableSelector);
        if (firstFocusable) {
          firstFocusable.focus();
        } else {
          dialogRef.current.focus();
        }
      }
    }, 0);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsShareOpen(false);
        return;
      }

      if (e.key === "Tab" && dialogRef.current) {
        const focusableElements =
          dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector);
        if (focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        const currentActive = document.activeElement as HTMLElement | null;

        // If focus left the dialog or is on the container (e.g. control was disabled during update)
        if (
          !currentActive ||
          !dialogRef.current.contains(currentActive) ||
          currentActive === dialogRef.current
        ) {
          e.preventDefault();
          if (e.shiftKey) {
            lastElement.focus();
          } else {
            firstElement.focus();
          }
          return;
        }

        if (e.shiftKey) {
          if (currentActive === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (currentActive === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    const handleFocusIn = (e: FocusEvent) => {
      if (dialogRef.current && !dialogRef.current.contains(e.target as Node)) {
        const focusableElements =
          dialogRef.current.querySelectorAll<HTMLElement>(focusableSelector);
        if (focusableElements.length > 0) {
          focusableElements[0].focus();
        } else {
          dialogRef.current.focus();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    document.addEventListener("focusin", handleFocusIn);

    return () => {
      clearTimeout(focusTimer);
      window.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("focusin", handleFocusIn);
      previousFocusRef.current?.focus();
    };
  }, [isShareOpen]);

  const handleCopyLink = async () => {
    setCopyError(null);
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch (err) {
      console.error("Failed to copy link", err);
      setCopyError("Failed to copy link to clipboard.");
      setTimeout(() => setCopyError(null), 3000);
    }
  };

  const handleToggleVisibility = async () => {
    if (!job || isUpdatingVisibility) return;
    const newPublicState = !job.is_public;
    setIsUpdatingVisibility(true);
    setVisibilityError(null);

    // Optimistic local state update
    setJob((prev) => (prev ? { ...prev, is_public: newPublicState } : prev));
    try {
      const updated = await api.updateVisibility(job.id, newPublicState);
      // Merge only the confirmed is_public status to prevent clobbering active polling results
      setJob((prev) =>
        prev ? { ...prev, is_public: updated.is_public } : prev,
      );
    } catch (err) {
      console.error("Failed to toggle visibility", err);
      setVisibilityError(
        err instanceof Error ? err.message : "Failed to update visibility.",
      );
      // Rollback on failure
      setJob((prev) => (prev ? { ...prev, is_public: !newPublicState } : prev));
    } finally {
      setIsUpdatingVisibility(false);
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
    return (
      <div className="max-w-md mx-auto my-auto p-8 text-center space-y-5">
        <div className="w-12 h-12 rounded-2xl bg-zinc-900 border border-white/[0.08] flex items-center justify-center mx-auto text-zinc-400">
          <Lock className="w-5 h-5 text-zinc-400" />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-lg font-semibold text-zinc-100">
            Research Not Found or Private
          </h2>
          <p className="text-xs text-zinc-400 leading-relaxed">
            {error ||
              "This research session does not exist, has been deleted, or is set to private by its author."}
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
        <div className="flex items-center justify-between gap-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>All Research</span>
          </Link>

          <div className="flex items-center gap-2">
            {!isOwner && (job.status === "completed" || job.status === "failed") && (
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
            )}

            <Button
              variant={isOwner && job.is_public ? "secondary" : "outline"}
              size="sm"
              onClick={isOwner ? () => setIsShareOpen(true) : handleCopyLink}
              className={
                isOwner && job.is_public
                  ? "border-emerald-500/30 text-emerald-300 hover:text-emerald-200"
                  : ""
              }
              leftIcon={
                isOwner ? (
                  job.is_public ? (
                    <Globe className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Share2 className="w-3.5 h-3.5" />
                  )
                ) : copiedLink ? (
                  <Check className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Share2 className="w-3.5 h-3.5" />
                )
              }
            >
              {isOwner
                ? job.is_public
                  ? "Shared"
                  : "Share"
                : copiedLink
                  ? "Copied"
                  : "Share"}
            </Button>
          </div>
        </div>

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

        {/* Copy Error Notice if any outside modal */}
        {copyError && !isShareOpen && (
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

            {/* Visibility Badge */}
            {isOwner ? (
              <button
                type="button"
                onClick={() => setIsShareOpen(true)}
                className="inline-flex items-center transition-opacity hover:opacity-80 cursor-pointer"
                title="Click to manage share settings"
              >
                {job.is_public ? (
                  <Badge
                    variant="outline"
                    className="text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                  >
                    <Globe className="w-3 h-3 mr-1 text-emerald-400" />
                    Public
                  </Badge>
                ) : (
                  <Badge
                    variant="neutral"
                    className="text-[10px] text-zinc-400 border-white/[0.08] bg-zinc-900/60"
                  >
                    <Lock className="w-3 h-3 mr-1 text-zinc-500" />
                    Private
                  </Badge>
                )}
              </button>
            ) : (
              <Badge
                variant="outline"
                className="text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
              >
                <Globe className="w-3 h-3 mr-1 text-emerald-400" />
                Shared report • Read-only
              </Badge>
            )}

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

      {/* Share Management Modal */}
      {isShareOpen && isOwner && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
          onClick={() => setIsShareOpen(false)}
        >
          <div
            ref={dialogRef}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="share-dialog-title"
            className="relative w-full max-w-md bg-[#121215] border border-white/[0.12] rounded-2xl shadow-2xl p-5 sm:p-6 space-y-5 focus:outline-none"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-white/[0.05] border border-white/[0.08] text-zinc-200">
                  <Share2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 id="share-dialog-title" className="text-sm font-semibold text-white">
                    Share Research
                  </h3>
                  <p className="text-[11px] text-zinc-400">
                    Manage link access and visibility
                  </p>
                </div>
              </div>
              <button
                type="button"
                aria-label="Close share dialog"
                onClick={() => setIsShareOpen(false)}
                className="p-1.5 rounded-lg text-zinc-400 hover:text-white hover:bg-white/[0.06] transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
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

            {/* Visibility Toggle Card */}
            <div className="p-4 rounded-xl bg-zinc-900/80 border border-white/[0.08] space-y-3">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div
                    className={`p-2 rounded-lg mt-0.5 ${
                      job.is_public
                        ? "bg-emerald-500/10 text-emerald-400"
                        : "bg-zinc-800 text-zinc-400"
                    }`}
                  >
                    {job.is_public ? (
                      <Globe className="w-4 h-4" />
                    ) : (
                      <Lock className="w-4 h-4" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-white">
                        {job.is_public
                          ? "Public Link Sharing"
                          : "Private Session"}
                      </span>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                          job.is_public
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-zinc-800 text-zinc-400 border border-white/[0.06]"
                        }`}
                      >
                        {job.is_public ? "Enabled" : "Disabled"}
                      </span>
                    </div>
                    <p className="text-[11px] text-zinc-400 mt-1 leading-relaxed">
                      {job.is_public
                        ? "Anyone with this link can view this report and import a copy to their session."
                        : "Only your session can view. Visitors following this link see a 404 Not Found."}
                    </p>
                  </div>
                </div>

                {/* Toggle Switch */}
                <button
                  type="button"
                  role="switch"
                  aria-checked={job.is_public}
                  aria-label="Public link sharing"
                  disabled={isUpdatingVisibility}
                  onClick={handleToggleVisibility}
                  className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/50 disabled:opacity-50 disabled:cursor-not-allowed ${
                    job.is_public ? "bg-emerald-500" : "bg-zinc-700"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out ${
                      job.is_public ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>
            </div>

            {/* Share Link Row (when public) */}
            {job.is_public ? (
              <div className="space-y-2">
                <label htmlFor="shareable-link-input" className="text-[11px] font-medium text-zinc-400">
                  Shareable link
                </label>
                <div className="flex items-center gap-2">
                  <input
                    id="shareable-link-input"
                    type="text"
                    readOnly
                    value={
                      typeof window !== "undefined" ? window.location.href : ""
                    }
                    className="flex-1 bg-zinc-900 border border-white/[0.1] rounded-xl px-3 py-2 text-xs text-zinc-200 font-mono select-all focus:outline-none focus:border-white/20"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleCopyLink}
                    leftIcon={
                      copiedLink ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )
                    }
                  >
                    {copiedLink ? "Copied" : "Copy"}
                  </Button>
                </div>
                {copyError && (
                  <p className="text-[11px] text-rose-400">{copyError}</p>
                )}
                <p className="text-[10px] text-zinc-500 leading-normal">
                  Tip: Anyone with this link can view the completed report and research steps without an account.
                </p>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-zinc-900/40 border border-white/[0.04] flex items-center gap-2.5 text-[11px] text-zinc-400">
                <Lock className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <span>
                  Enable public sharing to generate a public link for others to view this report.
                </span>
              </div>
            )}

            {/* Modal Footer */}
            <div className="pt-2 flex justify-end">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setIsShareOpen(false)}
              >
                Done
              </Button>
            </div>
          </div>
        </div>
      )}

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
