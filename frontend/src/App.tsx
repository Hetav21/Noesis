import { useState, useEffect } from 'react';
import axios from 'axios';
import { ResearchForm } from './components/ResearchForm';
import { ResearchLog } from './components/ResearchLog';
import { ResearchResult } from './components/ResearchResult';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';

const API_BASE_URL = 'http://localhost:8000/api';

interface LogEvent {
  timestamp: string;
  message: string;
  level?: 'info' | 'warning' | 'error' | 'success';
}

interface ResearchJobStatus {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  logs: LogEvent[];
  result: string | null;
}

function App() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<ResearchJobStatus['status']>('queued');
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [result, setResult] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const startResearch = async (query: string) => {
    setIsLoading(true);
    setJobId(null);
    setLogs([]);
    setResult('');
    setStatus('queued');
    try {
      const response = await axios.post<{ id: string }>(`${API_BASE_URL}/research`, { query });
      setJobId(response.data.id);
      setStatus('running');
      setLogs([{ timestamp: new Date().toISOString(), message: `Research job ${response.data.id} started.`, level: 'info' }]);
    } catch (error) {
      console.error('Error starting research:', error);
      setLogs(prev => [...prev, { timestamp: new Date().toISOString(), message: 'Failed to start research.', level: 'error' }]);
      setStatus('failed');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;

    if (jobId && (status === 'running' || status === 'queued')) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get<ResearchJobStatus>(`${API_BASE_URL}/research/${jobId}`);
          setLogs(response.data.logs);
          setResult(response.data.result || '');
          setStatus(response.data.status);

          if (response.data.status === 'completed' || response.data.status === 'failed') {
            clearInterval(interval);
          }
        } catch (error) {
          console.error('Error fetching job status:', error);
          setLogs(prev => [...prev, { timestamp: new Date().toISOString(), message: 'Failed to fetch job status.', level: 'error' }]);
          setStatus('failed');
          clearInterval(interval);
        }
      }, 2000);
    }

    return () => clearInterval(interval);
  }, [jobId, status]);

  const getStatusBadgeVariant = (currentStatus: ResearchJobStatus['status']) => {
    switch (currentStatus) {
      case 'completed': return 'success';
      case 'failed': return 'danger';
      case 'running': return 'warning';
      default: return 'default';
    }
  };

  return (
    <div className='min-h-screen bg-gray-50 text-gray-900 p-4'>
      <h1 className='text-4xl font-bold text-center mb-8 text-gray-900'>Deep Research Agent UI</h1>

      {!jobId ? (
        <ResearchForm onSubmit={startResearch} isLoading={isLoading} />
      ) : (
        <div className='max-w-7xl mx-auto'>
          <div className='flex items-center justify-between mb-4'>
            <h2 className='text-2xl font-semibold'>Research Job: {jobId}</h2>
            <Badge variant={getStatusBadgeVariant(status)}>{status}</Badge>
          </div>
          <div className='grid grid-cols-1 md:grid-cols-2 gap-4 h-[calc(100vh-200px)]'>
            <ResearchLog logs={logs} />
            <ResearchResult result={result} />
          </div>
          <div className='mt-4 text-center'>
            {(status === 'completed' || status === 'failed') && (
              <Button onClick={() => setJobId(null)}>Start New Research</Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;

