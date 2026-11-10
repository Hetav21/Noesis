const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    // In browser, default to the same-site /api rewrite proxy so SameSite=Lax session cookies
    // are transmitted reliably without cross-origin or third-party cookie restrictions.
    if (
      process.env.NEXT_PUBLIC_DIRECT_API === "true" &&
      process.env.NEXT_PUBLIC_API_URL
    ) {
      return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
    }
    return "/api";
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

let sessionBootstrapPromise: Promise<void> | null = null;

/**
 * Ensures an authenticated session is established before issuing concurrent session-dependent requests.
 * Eliminates races where simultaneous initial requests (e.g. list + suggestions) generate competing cookies.
 */
export const ensureSession = async (): Promise<void> => {
  if (typeof window === "undefined") return;
  if (!sessionBootstrapPromise) {
    sessionBootstrapPromise = (async () => {
      const res = await fetch(`${getBaseUrl()}/session/me`, {
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error(`Failed to initialize session: ${res.statusText}`);
      }
    })().catch((err) => {
      sessionBootstrapPromise = null;
      throw err;
    });
  }
  return sessionBootstrapPromise;
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
  is_public?: boolean;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const isNotFoundError = (err: unknown): boolean => {
  if (err instanceof ApiError) {
    return err.status === 404;
  }
  if (err && typeof err === "object" && "status" in err) {
    return (err as { status?: number }).status === 404;
  }
  if (err instanceof Error) {
    const msg = err.message.toLowerCase();
    return (
      msg.includes("private") ||
      msg.includes("not exist") ||
      msg.includes("not found")
    );
  }
  return false;
};

export const api = {
  createResearch: async (config: ResearchConfig): Promise<ResearchJob> => {
    await ensureSession();
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
    await ensureSession();
    const res = await fetch(`${getBaseUrl()}/research/${jobId}`, {
      credentials: "include",
    });
    if (!res.ok) {
      if (res.status === 404) {
        throw new ApiError(
          "This research session does not exist or is set to private by its author.",
          404,
        );
      }
      const err = await res.json().catch(() => ({}));
      throw new ApiError(
        err.detail || `Failed to fetch research session (${res.status})`,
        res.status,
      );
    }
    return res.json();
  },

  updateVisibility: async (
    jobId: string,
    isPublic: boolean,
  ): Promise<ResearchJob> => {
    await ensureSession();
    const res = await fetch(`${getBaseUrl()}/research/${jobId}/visibility`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ is_public: isPublic }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update research visibility");
    }
    return res.json();
  },

  forkResearch: async (jobId: string): Promise<ResearchJob> => {
    await ensureSession();
    const res = await fetch(`${getBaseUrl()}/research/${jobId}/fork`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to import research session");
    }
    return res.json();
  },

  listResearch: async (
    limit: number = 20,
    offset: number = 0,
  ): Promise<ResearchJob[]> => {
    await ensureSession();
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
    await ensureSession();
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

  claimResearch: async (jobId: string): Promise<ResearchJob> => {
    await ensureSession();
    const res = await fetch(`${getBaseUrl()}/research/${jobId}/claim`, {
      method: "POST",
      credentials: "include",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to claim research session");
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
      await ensureSession();
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
