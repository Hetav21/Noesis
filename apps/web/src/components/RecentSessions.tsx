"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api, type ResearchJob } from "@/lib/api";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/card";
import { ArrowUpRight, Trash2, RefreshCw, Globe } from "lucide-react";

export const RecentSessions: React.FC = () => {
  const [jobs, setJobs] = useState<ResearchJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<string | null>(null);
  const deletedIdsRef = React.useRef<Set<string>>(new Set());

  const loadJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listResearch(15, 0);
      const list = Array.isArray(data) ? data : [];
      setJobs(list.filter((j) => !deletedIdsRef.current.has(j.id)));
    } catch (err) {
      console.warn("Failed to load recent sessions", err);
      setError(
        "Could not reach backend service. Check if API server is running.",
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (confirm("Delete this research session?")) {
      setIsDeleting(id);
      deletedIdsRef.current.add(id);
      try {
        await api.deleteResearch(id);
        setJobs((prev) => prev.filter((j) => j.id !== id));
      } catch (err) {
        deletedIdsRef.current.delete(id);
        console.error("Failed to delete job", err);
        setError("Failed to delete research session. Please try again.");
      } finally {
        setIsDeleting(null);
      }
    }
  };

  const getStatusBadge = (status: ResearchJob["status"]) => {
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
            Running
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
          <Badge variant="neutral" dot>
            Queued
          </Badge>
        );
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  return (
    <Card className="border-white/[0.08]">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div>
          <CardTitle>Recent Research</CardTitle>
          <p className="text-xs text-zinc-500 mt-0.5">
            Past reports and active queries
          </p>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={loadJobs}
          isLoading={isLoading}
          leftIcon={<RefreshCw className="w-3 h-3" />}
          className="text-xs text-zinc-400 hover:text-zinc-200"
        >
          Refresh
        </Button>
      </CardHeader>

      <CardContent className="p-0">
        {error ? (
          <div className="py-8 px-6 text-center text-xs space-y-2">
            <p className="text-zinc-400 font-medium">
              Unable to load research history
            </p>
            <p className="text-zinc-500 max-w-sm mx-auto">
              Backend service was temporarily unreachable.
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={loadJobs}
              leftIcon={<RefreshCw className="w-3 h-3" />}
              className="mt-2 text-xs"
            >
              Retry
            </Button>
          </div>
        ) : isLoading && jobs.length === 0 ? (
          <div className="py-8 text-center text-xs text-zinc-500">
            <RefreshCw className="w-3.5 h-3.5 animate-spin mx-auto mb-2 text-zinc-400" />
            Loading history...
          </div>
        ) : jobs.length === 0 ? (
          <div className="py-10 px-6 text-center text-xs text-zinc-500 space-y-1">
            <p className="text-zinc-400 font-medium">No research history yet</p>
            <p className="text-zinc-500">
              Your completed research reports will be listed here.
            </p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.05]">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="p-3.5 sm:px-5 hover:bg-zinc-900/50 transition-colors duration-150 flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
              >
                <div className="space-y-1 flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getStatusBadge(job.status)}
                    {job.is_public && (
                      <Badge
                        variant="outline"
                        className="text-[10px] text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
                      >
                        <Globe className="w-2.5 h-2.5 mr-1 text-emerald-400" />
                        Public
                      </Badge>
                    )}
                    <span className="text-[11px] text-zinc-500 font-mono">
                      {formatDate(job.created_at)}
                    </span>
                    <span className="text-[11px] text-zinc-500">
                      • {job.depth} {job.depth === 1 ? "round" : "rounds"}
                    </span>
                  </div>
                  <Link
                    href={`/research/${job.id}`}
                    className="block font-medium text-sm text-zinc-200 hover:text-white transition-colors truncate"
                  >
                    {job.query}
                  </Link>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link href={`/research/${job.id}`}>
                    <Button
                      variant="secondary"
                      size="sm"
                      rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}
                    >
                      {job.status === "completed" ? "View Report" : "View"}
                    </Button>
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={isDeleting === job.id}
                    onClick={(e) => handleDelete(e, job.id)}
                    className="text-zinc-500 hover:text-red-400 h-8 w-8 p-0"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
