const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "/api";
  }
  if (process.env.BACKEND_URL) {
    const raw = process.env.BACKEND_URL.replace(/\/+$/, "").replace(/\/api$/, "");
    return `${raw}/api`;
  }
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  return "http://localhost:8000/api";
};


export interface ResearchConfig {
  query: string;
  depth: number;
  breadth: number;
}

export interface LogEvent {
  timestamp: string;
  message: string;
  level?: "info" | "warning" | "error" | "success";
  type?:
    | "status"
    | "info"
    | "section"
    | "list_item"
    | "error"
    | "warning"
    | "success"
    | "report";
  title?: string;
  content?: string;
}

export interface ResearchJob {
  id: string;
  query: string;
  depth: number;
  breadth: number;
  status: "queued" | "running" | "completed" | "failed";
  logs: LogEvent[];
  result: string | null;
  created_at: string;
  is_owner?: boolean;
}

export const api = {
  createResearch: async (config: ResearchConfig): Promise<ResearchJob> => {
    const res = await fetch(`${getBaseUrl()}/research`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to create research job");
    }
    return res.json();
  },

  getResearch: async (jobId: string): Promise<ResearchJob> => {
    const res = await fetch(`${getBaseUrl()}/research/${jobId}`, {
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Research job not found");
    }
    return res.json();
  },

  listResearch: async (
    limit: number = 20,
    offset: number = 0,
  ): Promise<ResearchJob[]> => {
    const res = await fetch(
      `${getBaseUrl()}/research?limit=${limit}&offset=${offset}`,
      {
        credentials: "include",
      },
    );
    if (!res.ok) {
      throw new Error("Failed to list research jobs");
    }
    return res.json();
  },

  deleteResearch: async (
    jobId: string,
  ): Promise<{ status: string; id: string }> => {
    const res = await fetch(`${getBaseUrl()}/research/${jobId}`, {
      method: "DELETE",
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to delete research job");
    }
    return res.json();
  },

  getHealth: async (): Promise<{
    status: string;
    service: string;
    timestamp: string;
  }> => {
    const res = await fetch(`${getBaseUrl()}/health`, {
      credentials: "include",
    });
    if (!res.ok) {
      throw new Error("Backend health check failed");
    }
    return res.json();
  },

  getSuggestions: async (refresh: boolean = false): Promise<string[]> => {
    try {
      const url = `${getBaseUrl()}/suggestions${refresh ? "?refresh=true" : ""}`;
      const res = await fetch(url, {
        credentials: "include",
      });
      if (!res.ok) return [];
      const data = await res.json();
      return Array.isArray(data.suggestions) ? data.suggestions : [];
    } catch {
      return [];
    }
  },
};
