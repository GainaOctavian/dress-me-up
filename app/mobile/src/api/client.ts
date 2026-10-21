import { API_BASE_URL } from "../config/constants";

// Set by AuthContext: any 401 (e.g. expired token) logs the user out.
let onUnauthorized: (() => void) | null = null;
export const setUnauthorizedHandler = (handler: (() => void) | null) => {
  onUnauthorized = handler;
};

// fetch that says which URL it couldn't reach (network errors name no host)
async function send(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (e) {
    throw new Error(`Could not reach ${url}: ${e instanceof Error ? e.message : String(e)}`);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (response.status === 401) onUnauthorized?.();
  if (!response.ok) {
    const text = await response.text();
    console.log("API error:", response.status, text);
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function requestJson<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await send(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  return handleResponse<T>(response);
}

async function requestForm<T>(
  path: string,
  body: URLSearchParams
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;

  const response = await send(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: body.toString(),
  });

  return handleResponse<T>(response);
}

export const apiClient = {
  get: <T>(path: string) => requestJson<T>(path, { method: "GET" }),

  getWithAuth: <T>(path: string, token: string) =>
    requestJson<T>(path, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    }),

  putWithAuth: <T>(path: string, token: string, body?: unknown) =>
    requestJson<T>(path, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: body ? JSON.stringify(body) : undefined,
    }),

  deleteWithAuth: <T>(path: string, token: string) =>
    requestJson<T>(path, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),

  postJsonWithAuth: <T>(path: string, token: string, body?: unknown) =>
    requestJson<T>(path, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: body ? JSON.stringify(body) : undefined,
    }),

  postJson: <T>(path: string, body?: unknown) =>
    requestJson<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  putJson: <T>(path: string, body?: unknown) =>
    requestJson<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string) =>
    requestJson<T>(path, { method: "DELETE" }),

  postForm: <T>(path: string, form: URLSearchParams) =>
    requestForm<T>(path, form),
};

// Errors are thrown as Error(responseText); FastAPI sends {"detail": "..."}.
// Returns that detail when it's a plain message, else the fallback.
export function errorMessage(e: unknown, fallback: string): string {
  try {
    const detail = JSON.parse((e as Error).message).detail;
    return typeof detail === "string" ? detail : fallback;
  } catch {
    return fallback;
  }
}
