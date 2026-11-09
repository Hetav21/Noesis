'use client';

import React, { useEffect, useState, use } from 'react';
import Link from 'next/link';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { api, type ResearchJob } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { ArrowLeft, Copy, Check, Download, Printer } from 'lucide-react';

interface RawPageProps {
  params: Promise<{ id: string }>;
}

export default function ResearchRawPage({ params }: RawPageProps) {
  const resolvedParams = use(params);
  const jobId = resolvedParams.id;
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.getResearch(jobId)
      .then((data) => setJob(data))
      .catch((err) => console.warn('Could not load report in raw mode:', err))
      .finally(() => setIsLoading(false));
  }, [jobId]);

  const handleCopy = async () => {
    if (!job?.result) return;
    try {
      await navigator.clipboard.writeText(job.result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDownload = () => {
    if (!job?.result) return;
    const sanitized = job.query.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40);
    const blob = new Blob([job.result], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research-${sanitized || 'report'}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#09090b] flex items-center justify-center p-8">
        <div className="text-zinc-500 text-sm">Loading report...</div>
      </div>
    );
  }

  if (!job || !job.result) {
    return (
      <div className="min-h-screen bg-[#09090b] flex flex-col items-center justify-center p-8 space-y-3">
        <div className="text-zinc-300 font-medium">Report not ready or not found</div>
        <Link href={`/research/${jobId}`}>
          <Button variant="secondary" size="sm" leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}>
            Back to session
          </Button>
        </Link>
      </div>
    );
  }

  const wordCount = job.result.trim().split(/\s+/).filter(Boolean).length;
  const readTime = Math.max(1, Math.ceil(wordCount / 220));

  return (
    <div className="min-h-screen bg-[#09090b] text-zinc-100 py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Top Floating Controls */}
        <div className="flex items-center justify-between pb-6 border-b border-white/[0.08] text-xs text-zinc-400">
          <Link
            href={`/research/${jobId}`}
            className="inline-flex items-center gap-1.5 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Workspace</span>
          </Link>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCopy}
              leftIcon={copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            >
              {copied ? 'Copied' : 'Copy'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              leftIcon={<Download className="w-3 h-3" />}
            >
              Export
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => window.print()}
              leftIcon={<Printer className="w-3 h-3" />}
            >
              Print
            </Button>
          </div>
        </div>

        {/* Document Header */}
        <div className="space-y-3">
          <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
            Research Brief • {new Date(job.created_at).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })}
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
            {job.query}
          </h1>
          <div className="flex items-center gap-3 text-xs text-zinc-500 font-mono pt-1">
            <span>{wordCount.toLocaleString()} words</span>
            <span>•</span>
            <span>~{readTime} min read</span>
            <span>•</span>
            <span>{job.depth} research {job.depth === 1 ? 'round' : 'rounds'}</span>
          </div>
        </div>

        {/* Document Body */}
        <article className="markdown-body pt-4 border-t border-white/[0.06]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {job.result}
          </ReactMarkdown>
        </article>
      </div>
    </div>
  );
}
