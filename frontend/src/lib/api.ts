import { config } from "@/lib/config";
import { tokenStore } from "@/lib/token";
import type { RegisterPayload, TokenResponse, User } from "@/types/auth";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && typeof init.body === "string") headers.set("Content-Type", "application/json");

  let res: Response;
  try {
    res = await fetch(`${config.apiUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the API running?");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, formatDetail(body?.detail) ?? res.statusText);
  }
  return (await res.json()) as T;
}

// FastAPI returns either a string or a list of validation errors.
function formatDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: string[]; msg?: string };
    const field = first.loc?.at(-1);
    return field ? `${field}: ${first.msg}` : (first.msg ?? null);
  }
  return null;
}

export const authApi = {
  register: (data: RegisterPayload) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify(data) }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: new URLSearchParams({ username: email, password }),
    }),

  me: () => request<User>("/users/me"),
};
