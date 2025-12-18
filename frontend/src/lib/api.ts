import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

export interface ResearchConfig {
  query: string;
  depth: number;
  breadth: number;
}

export interface LogEvent {
  timestamp: string;
  message: string;
  level?: 'info' | 'warning' | 'error' | 'success';
}

export interface ResearchJob {
  id: string;
  query: string;
  depth: number;
  breadth: number;
  status: 'queued' | 'running' | 'completed' | 'failed';
  logs: LogEvent[];
  result: string | null;
  created_at: string;
}

export const api = {
  createResearch: async (config: ResearchConfig): Promise<ResearchJob> => {
    const response = await axios.post<ResearchJob>(`${API_BASE_URL}/research`, config);
    return response.data;
  },
  
  getResearch: async (jobId: string): Promise<ResearchJob> => {
    const response = await axios.get<ResearchJob>(`${API_BASE_URL}/research/${jobId}`);
    return response.data;
  },
};
