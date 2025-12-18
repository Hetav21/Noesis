import React, { useEffect, useRef } from 'react';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface LogEvent {
  timestamp: string;
  message: string;
  level?: 'info' | 'warning' | 'error' | 'success';
}

interface ResearchLogProps {
  logs: LogEvent[];
}

export const ResearchLog: React.FC<ResearchLogProps> = ({ logs }) => {
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getBadgeVariant = (level?: LogEvent['level']) => {
    switch (level) {
      case 'error': return 'danger';
      case 'warning': return 'warning';
      case 'success': return 'success';
      default: return 'default';
    }
  };

  return (
    <Card className='h-full flex flex-col'>
      <h3 className='text-xl font-semibold mb-4 text-gray-900'>Research Log</h3>
      <div className='flex-grow overflow-y-auto space-y-2 p-2 bg-gray-100 rounded-md'>
        {logs.length === 0 ? (
          <p className='text-gray-500'>No logs yet. Start a research job to see updates.</p>
        ) : (
          logs.map((log, index) => (
            <div key={index} className='text-sm text-gray-700 flex items-start space-x-2'>
              <Badge variant={getBadgeVariant(log.level)} className='flex-shrink-0 mt-0.5'>
                {new Date(log.timestamp).toLocaleTimeString()}
              </Badge>
              <span className='flex-grow'>{log.message}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </Card>
  );
};
