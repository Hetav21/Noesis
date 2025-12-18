import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';

interface ResearchFormProps {
  onSubmit: (query: string, depth: number, breadth: number) => void;
  isLoading: boolean;
}

export const ResearchForm: React.FC<ResearchFormProps> = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState(2);
  const [breadth, setBreadth] = useState(4);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query, depth, breadth);
    }
  };

  return (
    <Card className='p-6 max-w-md mx-auto mt-10'>
      <h2 className='text-2xl font-bold mb-4 text-gray-900'>Start New Research</h2>
      <form onSubmit={handleSubmit} className='space-y-4'>
        <div>
          <label htmlFor='query' className='block text-sm font-medium text-gray-700 mb-1'>
            Research Query
          </label>
          <Input
            id='query'
            type='text'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g., How to implement OAuth in Next.js'
            disabled={isLoading}
          />
        </div>

        <div>
          <label htmlFor='depth' className='block text-sm font-medium text-gray-700 mb-1'>
            Research Depth: {depth}
          </label>
          <input
            id='depth'
            type='range'
            min='1'
            max='5'
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
            disabled={isLoading}
            className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
          />
          <div className='flex justify-between text-xs text-gray-500 mt-1'>
            <span>Quick (1)</span>
            <span>Deep (5)</span>
          </div>
        </div>

        <div>
          <label htmlFor='breadth' className='block text-sm font-medium text-gray-700 mb-1'>
            Search Breadth: {breadth}
          </label>
          <input
            id='breadth'
            type='range'
            min='2'
            max='10'
            value={breadth}
            onChange={(e) => setBreadth(Number(e.target.value))}
            disabled={isLoading}
            className='w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer'
          />
          <div className='flex justify-between text-xs text-gray-500 mt-1'>
            <span>Narrow (2)</span>
            <span>Wide (10)</span>
          </div>
        </div>

        <Button type='submit' disabled={isLoading} className='w-full'>
          {isLoading ? 'Starting Research...' : 'Start Research'}
        </Button>
      </form>
    </Card>
  );
};
