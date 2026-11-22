import type { ApiErrorPayload } from '../types/system';

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.PROD ? '/api/v1' : 'http://127.0.0.1:8000/api/v1')
).replace(/\/+$/, '');

export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code = 'API_ERROR') {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${API_BASE_URL}${normalizedPath}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    });
  } catch {
    throw new ApiClientError(
      'Unable to reach the local backend server. Verify FastAPI is running.',
      0,
      'NETWORK_ERROR'
    );
  }

  if (!response.ok) {
    let errorMessage = `Request failed with status ${response.status}`;
    let errorCode = `HTTP_${response.status}`;

    try {
      const payload = (await response.json()) as Partial<ApiErrorPayload>;
      if (payload.error?.message) {
        errorMessage = payload.error.message;
      }
      if (payload.error?.code) {
        errorCode = payload.error.code;
      }
    } catch {
      // Fall back to default error message when response is not JSON
    }

    throw new ApiClientError(errorMessage, response.status, errorCode);
  }

  return (await response.json()) as T;
}
