import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card } from './ui/card';

interface ResearchFormProps {
  onSubmit: (query: string) => void;
  isLoading: boolean;
}

export const ResearchForm: React.FC<ResearchFormProps> = ({ onSubmit, isLoading }) => {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSubmit(query);
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
        <Button type='submit' disabled={isLoading} className='w-full'>
          {isLoading ? 'Starting Research...' : 'Start Research'}
        </Button>
      </form>
    </Card>
  );
};
