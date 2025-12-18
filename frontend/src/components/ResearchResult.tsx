import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Card } from './ui/card';

interface ResearchResultProps {
  result: string;
}

export const ResearchResult: React.FC<ResearchResultProps> = ({ result }) => {
  return (
    <Card className='h-full flex flex-col p-6'>
      <h3 className='text-xl font-semibold mb-4 text-gray-900'>Research Result</h3>
      <div className='flex-grow overflow-y-auto p-4 bg-gray-100 rounded-md prose max-w-none'>
        {result ? (
          <ReactMarkdown>{result}</ReactMarkdown>
        ) : (
          <p className='text-gray-500'>Research result will appear here.</p>
        )}
      </div>
    </Card>
  );
};
