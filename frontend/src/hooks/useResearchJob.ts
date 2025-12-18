import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../lib/api';
import type { ResearchJob } from '../lib/api';

interface UseResearchJobResult {
  job: ResearchJob | null;
  isLoading: boolean;
  error: string | null;
}

export function useResearchJob(jobId: string | undefined): UseResearchJobResult {
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const statusRef = useRef<string>('queued');

  const fetchJob = useCallback(async () => {
    if (!jobId) return;
    try {
      const result = await api.getResearch(jobId);
      setJob(result);
      statusRef.current = result.status;
      setError(null);
    } catch (err) {
      setError('Research job not found');
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    fetchJob().then(() => setIsLoading(false));

    const interval = setInterval(() => {
      if (statusRef.current === 'running' || statusRef.current === 'queued') {
        fetchJob();
      } else {
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, fetchJob]);

  return { job, isLoading, error };
}
