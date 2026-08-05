// Typed API client + SWR fetcher. The base URL is provided at build/run time via
// NEXT_PUBLIC_API_BASE (e.g. http://localhost:8000/api/v1). All calls are GET
// (the platform is read-only in V1).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, { headers: { Accept: "application/json" } });
  } catch (err) {
    throw new ApiError(`Network error contacting API: ${(err as Error).message}`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      /* ignore body parse errors */
    }
    throw new ApiError(`${res.status} ${detail}`, res.status);
  }
  return (await res.json()) as T;
}

// SWR fetcher bound to the typed client.
export const fetcher = <T>(path: string): Promise<T> => apiGet<T>(path);

export function qs(params: Record<string, string | number | undefined | null>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null);
  if (entries.length === 0) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of entries) sp.set(k, String(v));
  return `?${sp.toString()}`;
}
