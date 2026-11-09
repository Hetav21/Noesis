'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { ResearchForm } from '@/components/ResearchForm';
import { RecentSessions } from '@/components/RecentSessions';

export default function HomePage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (query: string, depth: number, breadth: number) => {
    setIsLoading(true);
    setError(null);
    try {
      const job = await api.createResearch({ query, depth, breadth });
      router.push(`/research/${job.id}`);
    } catch (err: unknown) {
      console.error('Failed to create research job', err);
      const msg = err instanceof Error ? err.message : 'Failed to launch research session';
      setError(msg);
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12 sm:py-20 space-y-12">
      {/* Editorial Header */}
      <div className="text-center space-y-2.5 max-w-xl mx-auto">
        <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-zinc-100">
          What would you like to research?
        </h1>
        <p className="text-sm text-zinc-400 font-normal">
          Generates structured reports with cited web evidence and gap analysis.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-red-950/30 border border-red-500/20 text-red-300 text-xs sm:text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="text-xs font-mono underline hover:text-white cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Search Input */}
      <div>
        <ResearchForm onSubmit={handleSubmit} isLoading={isLoading} />
      </div>

      {/* Recent Sessions */}
      <div className="pt-4">
        <RecentSessions />
      </div>
    </div>
  );
}
