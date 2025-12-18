import { useState } from 'react';
import { useNavigate } from 'react-router';
import { ResearchForm } from '../components/ResearchForm';
import { api } from '../lib/api';

export function HomePage() {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (query: string, depth: number = 2, breadth: number = 4) => {
    setIsLoading(true);
    try {
      const job = await api.createResearch({ query, depth, breadth });
      navigate(`/research/${job.id}`);
    } catch (error) {
      console.error('Failed to create research job:', error);
      setIsLoading(false);
    }
  };

  return <ResearchForm onSubmit={handleSubmit} isLoading={isLoading} />;
}
