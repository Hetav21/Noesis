import { useParams, useNavigate } from 'react-router';
import { useResearchJob } from '../hooks/useResearchJob';
import { ResearchLog } from '../components/ResearchLog';
import { ResearchResult } from '../components/ResearchResult';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';

export function ResearchPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { job, isLoading, error } = useResearchJob(jobId);

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto text-center py-20">
        <div className="text-xl text-gray-600">Loading research job...</div>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-7xl mx-auto text-center py-20">
        <div className="text-xl text-red-600 mb-4">{error || 'Job not found'}</div>
        <Button onClick={() => navigate('/')}>Start New Research</Button>
      </div>
    );
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'success' as const;
      case 'failed': return 'danger' as const;
      case 'running': return 'warning' as const;
      default: return 'default' as const;
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Research Job</h2>
          <p className="text-sm text-gray-500 mt-1">ID: {job.id}</p>
        </div>
        <Badge variant={getStatusBadgeVariant(job.status)}>{job.status}</Badge>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-[calc(100vh-200px)]">
        <ResearchLog logs={job.logs} />
        <ResearchResult result={job.result || ''} />
      </div>
      <div className="mt-4 text-center">
        {(job.status === 'completed' || job.status === 'failed') && (
          <Button onClick={() => navigate('/')}>Start New Research</Button>
        )}
      </div>
    </div>
  );
}
